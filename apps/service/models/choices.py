ORDER_STATUS = (
    (0, "Pending"),
    (1, "Collecting"),
    (2, "Delivering"),
    (3, "Completed"),
    (4, "Canceled")
)

PAYMENT_STATUS = (
    (0, "Pending"),
    (1, "Hold"),
    (2, "Paid"),
    (3, "Cancelled"),
)

DELIVERY_TYPE = (
    (0, "Delivery"),
    (1, "Pickup"),
)

PAYMENT_TYPE = (
    (1, "Click"),
    (2, "Payme"),
    (3, "Uzum Bank"),
    (4, "При получении"),
)

CASH_PAYMENT_METHOD = (
    ("cash", "Наличные"),
    ("card", "Карта"),
)

ORDER_EVENT_CREATED = "order.created"
ORDER_EVENT_COLLECTING = "order.collecting"
ORDER_EVENT_CANCELED = "order.canceled"
ORDER_EVENT_REFUNDED = "order.refunded"
ORDER_EVENT_SYNC_FAILED = "order.sync_failed"

ORDER_EVENT_TYPE = (
    (ORDER_EVENT_CREATED, "Заказ создан"),
    (ORDER_EVENT_COLLECTING, "Заказ передан в сборку"),
    (ORDER_EVENT_CANCELED, "Заказ отменён"),
    (ORDER_EVENT_REFUNDED, "Возврат средств"),
    (ORDER_EVENT_SYNC_FAILED, "Ошибка синхронизации с 1С"),
)

OUTBOX_PENDING = "pending"
OUTBOX_SENT = "sent"
OUTBOX_FAILED = "failed"

OUTBOX_STATUS = (
    (OUTBOX_PENDING, "В очереди"),
    (OUTBOX_SENT, "Отправлено"),
    (OUTBOX_FAILED, "Ошибка"),
)
