"""One answer of the assistant. The POST endpoint and the WebSocket both call `reply`.

The model calls the tools (`tools.py`) up to MAX_TOOL_ROUNDS times, then answers. Products it recommends are
marked `[[p:ID]]` in its text; the markers are cut out and become the cards of the answer — only ids a tool
returned for this answer, so the card (with the live price) is always a real, active product.
"""
import logging
import re
import time

from django.conf import settings
from django.core.cache import cache
from django.db.models import F
from django.utils import timezone
from google.genai import types

from apps.service.models import AssistantConversation, AssistantMessage, Product
from . import budget, gemini, pii, prompts, tools
from .gemini import AssistantError

logger = logging.getLogger(__name__)

MAX_TOOL_ROUNDS = 4     # tool calls of one answer; the next round must answer with text
HISTORY_MESSAGES = 10   # earlier messages of the conversation sent to the model
MAX_PRODUCTS = 8        # product cards of one answer
MESSAGE_MAX_LENGTH = 1000
LIMIT_TTL = 2 * 24 * 3600
MINUTE_TTL = 120

MARKER = re.compile(r"\[\[\s*p\s*:\s*(\d+)\s*\]\]")
OPERATOR_MARKER = re.compile(r"\[\[\s*operator\s*\]\]", re.IGNORECASE)
MARKER_MAX_LENGTH = 24  # "[[" not closed within this many chars is plain text

FALLBACK_TEXT = {
    "uz": "Kechirasiz, hozir javob bera olmadim. Savolingizni boshqacharoq yozib ko'ring.",
    "ru": "Извините, сейчас не получилось ответить. Попробуйте сформулировать вопрос иначе.",
}


class AssistantDisabled(Exception):
    pass


class LimitExceeded(Exception):
    """The daily limit is used up."""


class TooFrequent(LimitExceeded):
    """The per-minute limit is used up."""


def check_enabled():
    """AssistantDisabled when switched off or the month's / day's Gemini budget is spent."""
    if not settings.ASSISTANT_ENABLED or budget.exhausted():
        raise AssistantDisabled()


def identity(viewer, ip):
    """Who the limit and the conversations belong to: the customer, else the device / cart, else the IP."""
    return viewer.identity or f"ip:{ip or 'unknown'}"


def _count(key, ttl):
    cache.add(key, 0, ttl)
    try:
        return cache.incr(key)
    except ValueError:  # the key expired between add and incr
        cache.set(key, 1, ttl)
        return 1


def take_limit(who, is_customer, ip=""):
    """Count one message of `who` (and of a guest's IP); TooFrequent / LimitExceeded once a limit is used up.

    A customer is counted by the account only (customers of one office share an IP)."""
    now = timezone.now()
    day, minute = now.date().isoformat(), now.strftime("%Y%m%d%H%M")
    daily = settings.ASSISTANT_DAILY_LIMIT_CUSTOMER if is_customer else settings.ASSISTANT_DAILY_LIMIT_GUEST
    counters = [(f"assistant:limit:m:{who}:{minute}", MINUTE_TTL, settings.ASSISTANT_MINUTE_LIMIT, TooFrequent),
                (f"assistant:limit:{who}:{day}", LIMIT_TTL, daily, LimitExceeded)]
    if not is_customer and ip:
        counters += [
            (f"assistant:limit:m:ip:{ip}:{minute}", MINUTE_TTL, settings.ASSISTANT_IP_MINUTE_LIMIT, TooFrequent),
            (f"assistant:limit:ip:{ip}:{day}", LIMIT_TTL, settings.ASSISTANT_IP_DAILY_LIMIT, LimitExceeded),
        ]
    exceeded = [error for key, ttl, limit, error in counters if _count(key, ttl) > limit]
    if exceeded:
        raise exceeded[0]()


def owned_conversation(conversation_id, viewer, who):
    """The conversation if it belongs to this viewer, else None."""
    if not conversation_id:
        return None
    qs = AssistantConversation.objects.filter(pk=conversation_id)
    if viewer.customer_id:
        return qs.filter(customer_id=viewer.customer_id).first()
    return qs.filter(customer__isnull=True, session_id=who).first()


def conversation_for(conversation_id, viewer, who, language, platform):
    """The viewer's conversation `conversation_id`; another one's or a missing one -> a new conversation."""
    conversation = owned_conversation(conversation_id, viewer, who)
    if conversation is None:
        conversation = AssistantConversation.objects.create(
            customer_id=viewer.customer_id, session_id="" if viewer.customer_id else who,
            language=language, platform=platform or "")
    return conversation


class MarkerFilter:
    """Cuts the `[[p:ID]]` / `[[operator]]` markers out of the model's text, also when a marker is split between
    chunks."""

    def __init__(self):
        self.buffer = ""
        self.ids = []
        self.operator = False
        self.pieces = []

    def feed(self, chunk):
        """The text of `chunk` that can be shown now (a possible start of a marker is held back)."""
        self.buffer += chunk
        out = []
        while True:
            start = self.buffer.find("[[")
            if start < 0:
                keep = 1 if self.buffer.endswith("[") else 0
                out.append(self.buffer[:len(self.buffer) - keep])
                self.buffer = self.buffer[len(self.buffer) - keep:]
                break
            out.append(self.buffer[:start])
            rest = self.buffer[start:]
            end = rest.find("]]")
            if end < 0:
                if len(rest) > MARKER_MAX_LENGTH:  # not a marker
                    out.append(rest[:2])
                    self.buffer = rest[2:]
                    continue
                self.buffer = rest
                break
            marker = rest[:end + 2]
            match = MARKER.fullmatch(marker)
            if match:
                pk = int(match.group(1))
                if pk not in self.ids:
                    self.ids.append(pk)
            elif OPERATOR_MARKER.fullmatch(marker):
                self.operator = True
            else:
                out.append(marker)
            self.buffer = rest[end + 2:]
        visible = "".join(out)
        self.pieces.append(visible)
        return visible

    def flush(self):
        rest, self.buffer = self.buffer, ""
        self.pieces.append(rest)
        return rest

    @property
    def text(self):
        return "".join(self.pieces)


def clean_text(text):
    """The answer text without the gaps the cut markers leave."""
    text = re.sub(r"[ \t]+([,.;:!?)])", r"\1", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    return text.strip()


class Usage:
    def __init__(self):
        self.input_tokens = 0
        self.output_tokens = 0

    def add(self, metadata):
        if metadata is None:
            return
        self.input_tokens += metadata.prompt_token_count or 0
        self.output_tokens += (metadata.candidates_token_count or 0) + (metadata.thoughts_token_count or 0)


def model_config(language, allow_tools=True):
    config = {
        "system_instruction": prompts.system_prompt(language),
        "tools": [types.Tool(function_declarations=[types.FunctionDeclaration(**declaration)
                                                    for declaration in tools.DECLARATIONS])],
        "temperature": settings.GEMINI_TEMPERATURE,
        "max_output_tokens": settings.GEMINI_MAX_OUTPUT_TOKENS,
        "automatic_function_calling": types.AutomaticFunctionCallingConfig(disable=True),
    }
    if not allow_tools:  # the last round: the history has tool calls, so the tools stay declared but off
        config["tool_config"] = types.ToolConfig(
            function_calling_config=types.FunctionCallingConfig(mode=types.FunctionCallingConfigMode.NONE))
    return types.GenerateContentConfig(**config)


def history(conversation, before_id):
    """The last HISTORY_MESSAGES messages before `before_id` (failed ones left out) as model contents;
    shown products as `[shown products: id: name]`."""
    messages = list(conversation.messages.filter(id__lt=before_id, error="").exclude(text="")
                    .order_by("-id")[:HISTORY_MESSAGES])[::-1]
    product_ids = {pk for message in messages for pk in message.product_ids}
    names = dict(Product.objects.filter(pk__in=product_ids).values_list("pk", "name")) if product_ids else {}
    contents = []
    for message in messages:
        text = message.text
        if message.role == AssistantMessage.ASSISTANT and message.product_ids:
            shown = "; ".join(f"{pk}: {names[pk]}" for pk in message.product_ids if pk in names)
            text = f"{text}\n[shown products: {shown}]" if shown else text
        contents.append(types.Content(role="model" if message.role == AssistantMessage.ASSISTANT else "user",
                                      parts=[types.Part.from_text(text=text)]))
    return contents


def _parts(response):
    candidates = response.candidates or []
    if not candidates or candidates[0].content is None:
        return []
    return list(candidates[0].content.parts or [])


def _visible(part):
    return part.text if part.text and not part.thought else ""


def _round(contents, config, marker, emit, stream):
    """One model call -> (its parts, usage metadata); text goes through the marker filter (and out if stream)."""
    if not stream:
        response = gemini.generate(contents, config)
        parts = _parts(response)
        for part in parts:
            marker.feed(_visible(part))
        return parts, response.usage_metadata
    parts, metadata = [], None
    for chunk in gemini.generate_stream(contents, config):
        metadata = chunk.usage_metadata or metadata  # the last chunk carries the totals
        for part in _parts(chunk):
            parts.append(part)
            visible = marker.feed(_visible(part))
            if visible:
                emit("delta", {"text": visible})
    return parts, metadata


def client_ip(meta):
    forwarded = (meta.get("HTTP_X_FORWARDED_FOR") or "").split(",")[0].strip()
    return forwarded or meta.get("REMOTE_ADDR") or ""


def question_data(question):
    """The customer's message as saved (phone / card numbers masked): the client shows this text."""
    return {"id": question.pk, "text": question.text, "pii_masked": question.pii_masked}


def begin(viewer, ip, text, conversation_id, language, platform):
    """Everything before the model call (POST and WebSocket): switch + budget, limits, conversation, the two
    rows of the exchange (the customer's message with phone / card numbers masked, and the answer, empty until
    `reply` fills it). Returns (conversation, question, answer).

    Raises AssistantDisabled / LimitExceeded / TooFrequent.
    """
    check_enabled()
    who = identity(viewer, ip)
    take_limit(who, bool(viewer.customer_id), ip)
    conversation = conversation_for(conversation_id, viewer, who, language, platform)
    text, masked = pii.mask(text)
    question = AssistantMessage.objects.create(conversation=conversation, role=AssistantMessage.USER, text=text,
                                               pii_masked=masked)
    answer = AssistantMessage.objects.create(conversation=conversation, role=AssistantMessage.ASSISTANT)
    answer.question_id = question.pk  # not a field: `_save` marks the question too when the answer fails
    return conversation, question, answer


def reply(conversation, question, answer, language, request, on_event=None):
    """Fill `answer` (the row from `begin`) and return {conversation_id, message_id, question, text, products}.

    `on_event(type, data)` (WebSocket) streams: "tool" {name} before every tool call, "delta" {text} chunks.
    Raises AssistantError when Gemini fails (the row keeps the error).
    """
    started = time.monotonic()
    emit = on_event or (lambda kind, data: None)
    # the customer's message is the last one of the history (`begin` saved it)
    contents = history(conversation, answer.pk)
    if not contents or contents[-1].role != "user":
        contents.append(types.Content(role="user", parts=[types.Part.from_text(text=question.text)]))
    ctx = tools.ToolContext(language=language)
    marker = MarkerFilter()
    usage = Usage()
    calls = []
    try:
        for number in range(MAX_TOOL_ROUNDS + 1):
            config = model_config(language, allow_tools=number < MAX_TOOL_ROUNDS)
            parts, metadata = _round(contents, config, marker, emit, stream=on_event is not None)
            usage.add(metadata)
            function_calls = [part.function_call for part in parts if part.function_call]
            if not function_calls:
                break
            # the model's turn goes back unchanged: Gemini 3 checks the thought signatures in it
            contents.append(types.Content(role="model", parts=parts))
            responses = []
            for call in function_calls:
                emit("tool", {"name": call.name})
                result = tools.run(call.name, call.args, ctx)
                calls.append({"name": call.name, "args": dict(call.args or {}), "count": tools.result_count(result)})
                responses.append(types.Part.from_function_response(name=call.name, response=result))
            contents.append(types.Content(role="user", parts=responses))
        tail = marker.flush()
        if tail:
            emit("delta", {"text": tail})
    except AssistantError as error:
        _save(conversation, answer, error=str(error) or "error", tool_calls=calls, usage=usage, started=started)
        raise

    final = clean_text(marker.text) or FALLBACK_TEXT.get(language, FALLBACK_TEXT["ru"])
    product_ids = [pk for pk in marker.ids if pk in ctx.seen_ids][:MAX_PRODUCTS]
    operator = marker.operator or question.pii_masked
    _save(conversation, answer, text=final, product_ids=product_ids, tool_calls=calls, usage=usage, started=started,
          operator=operator)
    return {
        "conversation_id": conversation.pk,
        "message_id": answer.pk,
        "question": question_data(question),
        "text": final,
        "operator": operator,
        "products": product_cards(product_ids, request),
    }


def product_cards(ids, request):
    """`ProductSerializer` cards of `ids` + `stock_status` (the rule the model is told, `tools.stock_status`)."""
    from apps.service.api.v1.client.views import linked_products_data  # the views import this module

    if not ids:
        return []
    cards = linked_products_data(ids, request)
    quantities = dict(Product.objects.filter(pk__in=ids).values_list("pk", "quantity"))
    for card in cards:
        card["stock_status"] = tools.stock_status(quantities.get(card["id"], 0))
    return cards


def _save(conversation, answer, *, text="", product_ids=(), tool_calls=(), usage, started, error="",
          operator=False):
    answer.text = text
    answer.show_operator = operator
    answer.product_ids = list(product_ids)
    answer.tool_calls = list(tool_calls)
    answer.input_tokens = usage.input_tokens
    answer.output_tokens = usage.output_tokens
    answer.latency_ms = int((time.monotonic() - started) * 1000)
    answer.error = error[:500]
    answer.model = settings.GEMINI_MODEL
    answer.cost_usd = budget.cost(usage.input_tokens, usage.output_tokens)
    answer.save(update_fields=["text", "product_ids", "tool_calls", "input_tokens", "output_tokens",
                               "latency_ms", "error", "model", "cost_usd", "show_operator", "updated_at"])
    AssistantConversation.objects.filter(pk=conversation.pk).update(
        messages_count=F("messages_count") + 2,
        input_tokens=F("input_tokens") + usage.input_tokens,
        output_tokens=F("output_tokens") + usage.output_tokens,
    )
    if error:
        # a question without an answer is left out of the next answers' history
        AssistantMessage.objects.filter(pk=getattr(answer, "question_id", None)).update(error=error[:500])
        logger.warning("assistant answer %s failed: %s", answer.pk, error)
    try:
        budget.after_answer()
    except Exception:
        logger.exception("assistant budget check failed")


def conversation_messages(conversation, request):
    """The conversation for the client: answered messages, oldest first, with their product cards."""
    messages = list(conversation.messages.filter(error="").exclude(text=""))
    ids = list(dict.fromkeys(pk for message in messages for pk in message.product_ids))
    cards = {card["id"]: card for card in product_cards(ids, request)}
    return {
        "conversation_id": conversation.pk,
        "messages": [
            {"id": message.pk, "role": message.role, "text": message.text, "created_at": message.created_at,
             "pii_masked": message.pii_masked, "operator": message.show_operator,
             "products": [cards[pk] for pk in message.product_ids if pk in cards]}
            for message in messages
        ],
    }
