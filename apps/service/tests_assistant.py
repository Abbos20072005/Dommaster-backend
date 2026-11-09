"""AI assistant: POST assistant/chat/, conversations, the WebSocket. Gemini is mocked (scripted responses).

Run: env/Scripts/python.exe manage.py test apps.service.tests_assistant
"""
import asyncio
import copy
import time
from unittest import mock

from asgiref.sync import async_to_sync
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.core.cache import cache
from django.test import override_settings
from google.genai import types
from rest_framework.test import APIClient

from apps.authorization.api.v1.client.views import issue_customer_tokens
from apps.service.assistant import consumers, service, tools
from apps.service.assistant.gemini import AssistantError
from apps.service.models import AssistantConversation, AssistantMessage
from apps.service.routing import websocket_urlpatterns
from apps.service.tests import ApiTestCase, make_customer, make_item_category, make_product

CHAT = "/api/v1/assistant/chat/"
GENERATE = "apps.service.assistant.gemini.generate"
GENERATE_STREAM = "apps.service.assistant.gemini.generate_stream"
LOCMEM = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": "assistant-tests"}}
ON = dict(ASSISTANT_ENABLED=1, ASSISTANT_DAILY_LIMIT_GUEST=20, ASSISTANT_DAILY_LIMIT_CUSTOMER=60, CACHES=LOCMEM)


def text(value):
    return types.Part.from_text(text=value)


def call(name, **args):
    return types.Part(function_call=types.FunctionCall(name=name, args=args))


def response(*parts, prompt=100, output=20):
    return types.GenerateContentResponse(
        candidates=[types.Candidate(content=types.Content(role="model", parts=list(parts)))],
        usage_metadata=types.GenerateContentResponseUsageMetadata(
            prompt_token_count=prompt, candidates_token_count=output),
    )


class Script:
    """A fake `gemini.generate`: returns the scripted responses in turn, keeps a copy of what it was sent."""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.sent = []

    def __call__(self, contents, config):
        self.sent.append((copy.deepcopy(contents), config))
        return self.responses.pop(0)


def catalog():
    _, tools_category = make_item_category("Asboblar")
    drill = make_product("P1", tools_category, 1_500_000, 1_200_000)
    drill.name_ru, drill.name_uz = "Перфоратор Bosch GBH 2-26", "Perforator Bosch GBH 2-26"
    drill.save()
    hammer = make_product("P2", tools_category, 90_000)
    hammer.name_ru, hammer.name_uz = "Молоток", "Bolg'a"
    hammer.save()
    return tools_category, drill, hammer


@override_settings(**ON)
class AssistantChatTests(ApiTestCase):
    def setUp(self):
        cache.clear()  # the daily limit counters
        self.category, self.drill, self.hammer = catalog()
        self.guest = APIClient(HTTP_X_DEVICE_ID="device-1", HTTP_ACCEPT_LANGUAGE="uz")

    def found_drill(self):
        return [
            response(call("search_products", queries=["perforator", "перфоратор"])),
            # the hammer was never returned by a tool and 999999 does not exist: neither may become a card
            response(text(f"Mana mos variant: Perforator Bosch [[p:{self.drill.pk}]], "
                          f"yana [[p:{self.hammer.pk}]] va [[p:999999]].")),
        ]

    def test_search_answer_with_cards(self):
        script = Script(*self.found_drill())
        with mock.patch(GENERATE, side_effect=script):
            result = self.guest.post(CHAT, {"message": "perforator kerak"}, format="json")
        self.assertEqual(result.status_code, 200, result.data)
        data = result.data["result"]
        self.assertEqual([card["id"] for card in data["products"]], [self.drill.pk])
        self.assertEqual(data["products"][0]["name"], "Perforator Bosch GBH 2-26")  # uz card
        self.assertNotIn("[[", data["text"])
        self.assertEqual(data["text"], "Mana mos variant: Perforator Bosch, yana va.")

        # the tool result went back to the model with the price the cart charges
        tool_turn = script.sent[1][0][-1].parts[0].function_response
        self.assertEqual(tool_turn.name, "search_products")
        self.assertEqual(tool_turn.response["products"][0]["price"], 1_200_000)
        self.assertEqual(tool_turn.response["products"][0]["old_price"], 1_500_000)

        answer = AssistantMessage.objects.get(pk=data["message_id"])
        self.assertEqual(answer.product_ids, [self.drill.pk])
        self.assertEqual(answer.tool_calls[0]["name"], "search_products")
        self.assertEqual(answer.tool_calls[0]["count"], 1)
        self.assertEqual((answer.input_tokens, answer.output_tokens), (200, 40))
        conversation = AssistantConversation.objects.get(pk=data["conversation_id"])
        self.assertEqual((conversation.messages_count, conversation.input_tokens, conversation.session_id),
                         (2, 200, "d:device-1"))
        self.assertIn("Uzbek", script.sent[0][1].system_instruction)

    def test_conversation_continues_with_history(self):
        with mock.patch(GENERATE, side_effect=Script(*self.found_drill())):
            first = self.guest.post(CHAT, {"message": "perforator kerak"}, format="json").data["result"]
        script = Script(response(text("Ha, u bor.")))
        with mock.patch(GENERATE, side_effect=script):
            second = self.guest.post(CHAT, {"message": "omborda bormi?", "conversation_id": first["conversation_id"]},
                                     format="json").data["result"]
        self.assertEqual(second["conversation_id"], first["conversation_id"])
        contents = script.sent[0][0]
        self.assertEqual([content.role for content in contents], ["user", "model", "user"])
        self.assertIn(f"[shown products: {self.drill.pk}: ", contents[1].parts[0].text)

    def test_foreign_conversation_starts_a_new_one(self):
        with mock.patch(GENERATE, side_effect=Script(response(text("Salom")))):
            first = self.guest.post(CHAT, {"message": "salom"}, format="json").data["result"]
        other = APIClient(HTTP_X_DEVICE_ID="device-2")
        with mock.patch(GENERATE, side_effect=Script(response(text("Salom")))):
            second = other.post(CHAT, {"message": "salom", "conversation_id": first["conversation_id"]},
                                format="json").data["result"]
        self.assertNotEqual(second["conversation_id"], first["conversation_id"])

    @override_settings(ASSISTANT_DAILY_LIMIT_GUEST=1)
    def test_daily_limit(self):
        with mock.patch(GENERATE, side_effect=Script(response(text("Salom")))):
            self.assertEqual(self.guest.post(CHAT, {"message": "salom"}, format="json").status_code, 200)
        with mock.patch(GENERATE) as generate:
            result = self.guest.post(CHAT, {"message": "yana"}, format="json")
        self.assertEqual((result.status_code, result.data["error_code"]), (429, 42))
        generate.assert_not_called()

    @override_settings(ASSISTANT_ENABLED=0)
    def test_switched_off(self):
        with mock.patch(GENERATE) as generate:
            result = self.guest.post(CHAT, {"message": "salom"}, format="json")
        self.assertEqual((result.status_code, result.data["error_code"]), (503, 41))
        generate.assert_not_called()

    def test_gemini_error(self):
        with mock.patch(GENERATE, side_effect=AssistantError("timeout")):
            result = self.guest.post(CHAT, {"message": "salom"}, format="json")
        self.assertEqual((result.status_code, result.data["error_code"]), (503, 43))
        self.assertEqual(AssistantMessage.objects.get(role=AssistantMessage.ASSISTANT).error, "timeout")
        # the unanswered question is not sent again with the next one
        conversation_id = AssistantConversation.objects.get().pk
        script = Script(response(text("Salom")))
        with mock.patch(GENERATE, side_effect=script):
            self.guest.post(CHAT, {"message": "yana", "conversation_id": conversation_id}, format="json")
        self.assertEqual([content.parts[0].text for content in script.sent[0][0]], ["yana"])

    def test_empty_message(self):
        result = self.guest.post(CHAT, {"message": "   "}, format="json")
        self.assertEqual((result.status_code, result.data["error_code"]), (400, 5))

    def test_no_personal_data_is_sent(self):
        customer = make_customer("+998901234567")
        customer.full_name = "Sardor Aliyev"
        customer.save()
        script = Script(response(text("Salom")))
        with mock.patch(GENERATE, side_effect=script):
            result = self.client_for(customer).post(CHAT, {"message": "salom"}, format="json")
        self.assertEqual(result.status_code, 200, result.data)
        sent = repr(script.sent)
        self.assertNotIn("Sardor", sent)
        self.assertNotIn("901234567", sent)
        self.assertEqual(AssistantConversation.objects.get().customer, customer)

    def test_tool_rounds_are_limited(self):
        script = Script(*[response(call("search_products", queries=["kabel"]))
                          for _ in range(service.MAX_TOOL_ROUNDS + 1)])
        with mock.patch(GENERATE, side_effect=script):
            result = self.guest.post(CHAT, {"message": "kabel"}, format="json")
        self.assertEqual(result.status_code, 200, result.data)
        self.assertEqual(len(script.sent), service.MAX_TOOL_ROUNDS + 1)
        self.assertIsNone(script.sent[0][1].tool_config)
        self.assertEqual(script.sent[-1][1].tool_config.function_calling_config.mode,
                         types.FunctionCallingConfigMode.NONE)
        self.assertEqual(result.data["result"]["text"], service.FALLBACK_TEXT["uz"])

    def test_conversation_history_endpoint(self):
        with mock.patch(GENERATE, side_effect=Script(*self.found_drill())):
            first = self.guest.post(CHAT, {"message": "perforator kerak"}, format="json").data["result"]
        url = f"/api/v1/assistant/conversations/{first['conversation_id']}/"
        data = self.guest.get(url).data["result"]
        self.assertEqual([message["role"] for message in data["messages"]], ["user", "assistant"])
        self.assertEqual([card["id"] for card in data["messages"][1]["products"]], [self.drill.pk])
        result = APIClient(HTTP_X_DEVICE_ID="device-2").get(url)
        self.assertEqual((result.status_code, result.data["error_code"]), (404, 4))


class AssistantToolTests(ApiTestCase):
    def setUp(self):
        self.category, self.drill, self.hammer = catalog()
        self.ctx = tools.ToolContext(language="ru")

    def test_search_filters(self):
        self.drill.quantity = 0
        self.drill.save()
        found = tools.search_products(self.ctx, queries=["перфоратор"])
        self.assertEqual([row["id"] for row in found["products"]], [self.drill.pk])
        self.assertFalse(found["products"][0]["in_stock"])
        self.assertEqual(found["categories"], [{"id": self.category.pk, "name": "Asboblar", "count": 1}])
        self.assertEqual(tools.search_products(self.ctx, queries=["перфоратор"], in_stock_only=True)["products"], [])
        self.assertEqual(tools.search_products(self.ctx, queries=["перфоратор"], price_max=100)["products"], [])
        self.assertEqual(self.ctx.seen_ids, {self.drill.pk})

    def test_category_without_words(self):
        found = tools.search_products(self.ctx, item_category_id=self.category.pk)
        self.assertEqual({row["id"] for row in found["products"]}, {self.drill.pk, self.hammer.pk})

    def test_hidden_product(self):
        self.drill.is_active = False
        self.drill.save()
        self.assertEqual(tools.search_products(self.ctx, queries=["перфоратор"])["products"], [])
        self.assertIn("error", tools.get_product_details(self.ctx, self.drill.pk))

    def test_bad_call_is_answered(self):
        self.assertIn("error", tools.run("search_products", {"nonsense": 1}, self.ctx))
        self.assertIn("error", tools.run("drop_tables", {}, self.ctx))


class MarkerFilterTests(ApiTestCase):
    def test_markers_split_between_chunks(self):
        marker = service.MarkerFilter()
        shown = [marker.feed(chunk) for chunk in ("Bosch [", "[p:1", "2]] yaxshi [[x]] va [[p:3]]", " [")]
        shown.append(marker.flush())
        self.assertNotIn("[[p", "".join(shown))
        self.assertEqual(marker.ids, [12, 3])
        self.assertEqual(service.clean_text(marker.text), "Bosch yaxshi [[x]] va [")


def stream(*parts_per_chunk, delay=0):
    """A fake generate_stream call: one chunk per item."""
    def chunks():
        for parts in parts_per_chunk:
            if delay:
                time.sleep(delay)
            yield response(*parts, prompt=50, output=5)
    return chunks()


@override_settings(**ON)
class AssistantSocketTests(ApiTestCase):
    """The answer runs in the test's thread (THREAD_SENSITIVE), so it sees the rows of the test transaction."""

    def setUp(self):
        self.category, self.drill, self.hammer = catalog()
        cache.clear()
        # the answer runs in the test's thread and must keep its connection (the test transaction)
        for patcher in (mock.patch.object(consumers, "THREAD_SENSITIVE", True),
                        mock.patch("channels.db.close_old_connections")):
            patcher.start()
            self.addCleanup(patcher.stop)

    def talk(self, path, *messages, until=1):
        """Send `messages`, collect events until `until` done / error events came."""
        async def run():
            communicator = WebsocketCommunicator(URLRouter(websocket_urlpatterns), path)
            connected, _ = await communicator.connect()
            self.assertTrue(connected)
            for message in messages:
                await communicator.send_json_to(message)
            events, finished = [], 0
            while finished < until:
                event = await communicator.receive_json_from(timeout=10)
                events.append(event)
                finished += event["type"] in ("done", "error")
            await communicator.disconnect()
            return events
        return async_to_sync(run)()

    def scripted_stream(self, delay=0):
        rounds = [
            stream([call("search_products", queries=["перфоратор"])], delay=delay),
            stream([text("Mana: Perforator [[p:")], [text(f"{self.drill.pk}]] juda mos.")], delay=delay),
        ]
        return lambda contents, config: rounds.pop(0)

    def test_guest_stream(self):
        with mock.patch(GENERATE_STREAM, side_effect=self.scripted_stream()):
            events = self.talk("/ws/assistant/?device_id=dev-1&lang=uz",
                               {"type": "message", "message": "perforator"})
        kinds = [event["type"] for event in events]
        self.assertEqual(kinds[0], "start")
        self.assertEqual(kinds[1], "tool")
        self.assertEqual(kinds[-1], "done")
        self.assertTrue(set(kinds[2:-1]) <= {"delta"})
        deltas = "".join(event["text"] for event in events if event["type"] == "delta")
        self.assertNotIn("[[", deltas)
        done = events[-1]
        self.assertEqual(done["text"], "Mana: Perforator juda mos.")
        self.assertEqual([card["id"] for card in done["products"]], [self.drill.pk])
        self.assertEqual(done["products"][0]["name"], "Perforator Bosch GBH 2-26")
        conversation = AssistantConversation.objects.get()
        self.assertEqual((conversation.session_id, conversation.language), ("d:dev-1", "uz"))

    def test_customer_token(self):
        customer = make_customer("+998900000077")
        access, _ = issue_customer_tokens(customer)
        with mock.patch(GENERATE_STREAM, side_effect=self.scripted_stream()):
            events = self.talk(f"/ws/assistant/?token={access}", {"type": "message", "message": "perforator"})
        self.assertEqual(events[-1]["type"], "done")
        self.assertEqual(AssistantConversation.objects.get().customer, customer)

    def test_bad_token_closes(self):
        async def run():
            communicator = WebsocketCommunicator(URLRouter(websocket_urlpatterns), "/ws/assistant/?token=bad")
            await communicator.connect()
            output = await communicator.receive_output(timeout=5)
            await communicator.wait()
            return output
        self.assertEqual(async_to_sync(run)(), {"type": "websocket.close", "code": 4001})

    def test_second_message_while_answering(self):
        # a slow answer without the db: in the test the answer shares the thread channels closes connections
        # in after every message, so a real one would hold the second message back until it is done
        async def slow_answer(consumer, data):
            await asyncio.sleep(0.3)
            await consumer.send_event({"type": "done", "text": data["message"]})

        with mock.patch.object(consumers.AssistantConsumer, "answer", slow_answer):
            events = self.talk("/ws/assistant/?device_id=dev-1",
                               {"type": "message", "message": "perforator"},
                               {"type": "message", "message": "yana"}, until=2)
        self.assertEqual(events[0], {"type": "error", "error_code": 5, "detail": "the previous answer is not done"})
        self.assertEqual(events[1], {"type": "done", "text": "perforator"})

    @override_settings(ASSISTANT_ENABLED=0)
    def test_switched_off(self):
        events = self.talk("/ws/assistant/?device_id=dev-1", {"type": "message", "message": "salom"})
        self.assertEqual(events, [{"type": "error", "error_code": 41, "detail": "The assistant is switched off"}])

    def test_gemini_error(self):
        def broken(contents, config):
            raise AssistantError("timeout")
            yield  # a generator, like the real one

        with mock.patch(GENERATE_STREAM, side_effect=broken):
            events = self.talk("/ws/assistant/?device_id=dev-1", {"type": "message", "message": "salom"})
        self.assertEqual([event["type"] for event in events], ["start", "error"])
        self.assertEqual(events[-1]["error_code"], 43)
