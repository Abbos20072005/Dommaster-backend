from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q

from apps.authorization.models import Customer
from apps.payment.models import (
    AtmosTransaction,
    ClickTransaction,
    MerchatTransactionsModel,
    UzumBankTransactionsModel,
)
from apps.service.models import (
    Comment,
    CommentImages,
    CommentReply,
    Order,
    OrderComment,
    OrderItem,
    OrderItemProjectChange,
    OrderOutboxEvent,
    OrderStatusChange,
    Product,
    Questions,
    QuestionsReply,
)

DEFAULT_TEST_PATTERNS = [
    "Pen Test",
    "888116646",
    "Jamoliddin",
    "Abbosbek",
    "Dilshodbek",
    "Rasul",
    "Shaxzod",
    "Bekzod",
]


class Command(BaseCommand):
    help = (
        "Deletes test data (orders, comments/reviews, questions) from the database for specific test users "
        "or all test records, and recalibrates product rating and counter fields."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simulate the deletion and output what would be deleted without making changes.",
        )
        parser.add_argument(
            "--all",
            action="store_true",
            help="Delete ALL orders, comments, and questions regardless of customer.",
        )
        parser.add_argument(
            "--customers",
            nargs="*",
            default=None,
            help=(
                "Custom list of customer names or phone numbers to filter. "
                f"Default test patterns: {', '.join(DEFAULT_TEST_PATTERNS)}"
            ),
        )
        parser.add_argument(
            "--orders",
            action="store_true",
            help="Delete only orders (and associated items, logs, payments).",
        )
        parser.add_argument(
            "--comments",
            action="store_true",
            help="Delete only comments/reviews (and replies, images).",
        )
        parser.add_argument(
            "--questions",
            action="store_true",
            help="Delete only questions (and replies).",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        clear_all = options["all"]
        delete_orders = options["orders"]
        delete_comments = options["comments"]
        delete_questions = options["questions"]
        custom_patterns = options["customers"]

        # Default to deleting all three categories if no specific flag was selected
        if not (delete_orders or delete_comments or delete_questions):
            delete_orders = True
            delete_comments = True
            delete_questions = True

        # Resolve target customers
        target_customers = None
        if not clear_all:
            patterns = custom_patterns if custom_patterns is not None else DEFAULT_TEST_PATTERNS
            q = Q()
            for pattern in patterns:
                q |= Q(full_name__icontains=pattern) | Q(phone_number__icontains=pattern)
            target_customers = Customer.objects.filter(q).distinct()

            self.stdout.write("--- Target Test Customers ---")
            if target_customers.exists():
                for c in target_customers:
                    self.stdout.write(f"  • ID {c.id}: {c.full_name or '(No name)'} ({c.phone_number})")
            else:
                self.stdout.write(self.style.WARNING("  No matching customers found!"))
        else:
            self.stdout.write(self.style.WARNING("--- Mode: --all (All customers and records) ---"))

        if dry_run:
            self.stdout.write(self.style.WARNING("\n=== DRY RUN MODE: No data will be permanently deleted ==="))

        with transaction.atomic():
            if delete_comments:
                self._clear_comments(target_customers=target_customers, dry_run=dry_run)

            if delete_questions:
                self._clear_questions(target_customers=target_customers, dry_run=dry_run)

            if delete_orders:
                self._clear_orders(target_customers=target_customers, dry_run=dry_run)

            if dry_run:
                self.stdout.write(self.style.WARNING("\n=== DRY RUN COMPLETE: Rolling back transaction ==="))
                transaction.set_rollback(True)
            else:
                self.stdout.write(self.style.SUCCESS("\n=== Successfully cleared test data! ==="))

    def _clear_comments(self, target_customers=None, dry_run=False):
        self.stdout.write("\n--- Processing Comments (Otziv) ---")
        if target_customers is not None:
            comments = Comment.objects.filter(customer__in=target_customers)
        else:
            comments = Comment.objects.all()

        comment_count = comments.count()
        comment_ids = list(comments.values_list("id", flat=True))
        product_ids = list(comments.values_list("product_id", flat=True).distinct())

        replies = CommentReply.objects.filter(comment_id__in=comment_ids)
        if target_customers is not None:
            replies = replies | CommentReply.objects.filter(customer__in=target_customers)
        reply_count = replies.count()

        images = CommentImages.objects.filter(comment_id__in=comment_ids)
        if target_customers is not None:
            images = images | CommentImages.objects.filter(customer__in=target_customers)
        image_count = images.count()

        self.stdout.write(
            f"Found: {comment_count} comments, {reply_count} comment replies, {image_count} comment images."
        )

        if not dry_run and comment_count > 0:
            for img in images:
                if img.image:
                    try:
                        img.image.delete(save=False)
                    except Exception as e:
                        self.stderr.write(f"Warning deleting comment image: {e}")

            images.delete()
            replies.delete()
            comments.delete()

            # Recalculate ratings and comment count for affected products
            for p in Product.objects.filter(id__in=product_ids):
                p.update_rating()

            self.stdout.write(
                self.style.SUCCESS(
                    f"Deleted {comment_count} comments, {reply_count} replies, {image_count} images. "
                    f"Recalculated ratings for {len(product_ids)} products."
                )
            )

    def _clear_questions(self, target_customers=None, dry_run=False):
        self.stdout.write("\n--- Processing Questions (Savollar) ---")
        if target_customers is not None:
            questions = Questions.objects.filter(customer__in=target_customers)
        else:
            questions = Questions.objects.all()

        question_count = questions.count()
        question_ids = list(questions.values_list("id", flat=True))
        product_ids = list(questions.values_list("product_id", flat=True).distinct())

        replies = QuestionsReply.objects.filter(question_id__in=question_ids)
        if target_customers is not None:
            replies = replies | QuestionsReply.objects.filter(customer__in=target_customers)
        reply_count = replies.count()

        self.stdout.write(f"Found: {question_count} questions, {reply_count} question replies.")

        if not dry_run and question_count > 0:
            replies.delete()
            questions.delete()

            # Recalculate questions count for affected products
            for p in Product.objects.filter(id__in=product_ids):
                p.update_questions()

            self.stdout.write(
                self.style.SUCCESS(
                    f"Deleted {question_count} questions, {reply_count} replies. "
                    f"Recalculated question count for {len(product_ids)} products."
                )
            )

    def _clear_orders(self, target_customers=None, dry_run=False):
        self.stdout.write("\n--- Processing Orders ---")
        if target_customers is not None:
            orders = Order.objects.filter(customer__in=target_customers)
        else:
            orders = Order.objects.all()

        order_count = orders.count()
        order_ids = list(orders.values_list("id", flat=True))

        item_count = OrderItem.objects.filter(order_id__in=order_ids).count()
        comment_count = OrderComment.objects.filter(order_id__in=order_ids).count()
        status_change_count = OrderStatusChange.objects.filter(order_id__in=order_ids).count()
        outbox_count = OrderOutboxEvent.objects.filter(order_id__in=order_ids).count()
        project_change_count = OrderItemProjectChange.objects.filter(order_id__in=order_ids).count()
        atmos_count = AtmosTransaction.objects.filter(order_id__in=order_ids).count()

        click_count = ClickTransaction.objects.filter(account_id__in=order_ids).count()
        payme_count = MerchatTransactionsModel.objects.filter(order_id__in=order_ids).count()
        uzum_count = UzumBankTransactionsModel.objects.filter(order_id__in=order_ids).count()

        self.stdout.write(
            f"Found: {order_count} orders, {item_count} order items, {comment_count} order comments, "
            f"{status_change_count} status changes, {outbox_count} outbox events, "
            f"{project_change_count} project changes, {atmos_count} Atmos transactions, "
            f"{click_count} Click transactions, {payme_count} Payme transactions, {uzum_count} Uzum transactions."
        )

        if not dry_run and order_count > 0:
            ClickTransaction.objects.filter(account_id__in=order_ids).delete()
            MerchatTransactionsModel.objects.filter(order_id__in=order_ids).delete()
            UzumBankTransactionsModel.objects.filter(order_id__in=order_ids).delete()

            AtmosTransaction.objects.filter(order_id__in=order_ids).delete()
            OrderItemProjectChange.objects.filter(order_id__in=order_ids).delete()
            OrderOutboxEvent.objects.filter(order_id__in=order_ids).delete()
            OrderStatusChange.objects.filter(order_id__in=order_ids).delete()
            OrderComment.objects.filter(order_id__in=order_ids).delete()
            OrderItem.objects.filter(order_id__in=order_ids).delete()
            orders.delete()

            self.stdout.write(
                self.style.SUCCESS(
                    f"Deleted {order_count} orders and all associated order items, outbox events, "
                    f"status logs, and test payment transactions."
                )
            )
