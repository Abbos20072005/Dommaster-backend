ORDER_PENDING, ORDER_CONFIRMED, ORDER_COLLECTING, ORDER_DELIVERING, ORDER_READY_FOR_PICKUP, ORDER_COMPLETED, \
    ORDER_CANCELED = range(7)
ORDER_STATUS = (
    (ORDER_PENDING, "Pending"),
    (ORDER_CONFIRMED, "Confirmed"),
    (ORDER_COLLECTING, "Collecting"),
    (ORDER_DELIVERING, "Delivering"),
    (ORDER_READY_FOR_PICKUP, "Ready for pickup"),
    (ORDER_COMPLETED, "Completed"),
    (ORDER_CANCELED, "Canceled"),
)

PAYMENT_PENDING, PAYMENT_HOLD, PAYMENT_PAID, PAYMENT_CANCELLED = range(4)
PAYMENT_STATUS = (
    (PAYMENT_PENDING, "Pending"),
    (PAYMENT_HOLD, "Hold"),
    (PAYMENT_PAID, "Paid"),
    (PAYMENT_CANCELLED, "Cancelled"),
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
# no longer offered to customers (launch audit B-03, 25.11.2026): the client checkout refuses it, old orders keep it
PAYMENT_ON_DELIVERY = 4

CASH_PAYMENT_METHOD = (
    ("cash", "Наличные"),
    ("card", "Карта"),
)

ORDER_CHANNEL_SITE = "site"
ORDER_CHANNEL_IOS = "ios"
ORDER_CHANNEL_ANDROID = "android"

# where the order was placed, the same values as the client `?platform=`
ORDER_CHANNEL = (
    (ORDER_CHANNEL_SITE, "Сайт"),
    (ORDER_CHANNEL_IOS, "iOS"),
    (ORDER_CHANNEL_ANDROID, "Android"),
)

ORDER_EVENT_CREATED = "order.created"
ORDER_EVENT_COLLECTING = "order.collecting"
ORDER_EVENT_CANCELED = "order.canceled"
ORDER_EVENT_REFUNDED = "order.refunded"
ORDER_EVENT_SYNC_FAILED = "order.sync_failed"
ORDER_EVENT_PICKUP_SELECTED = "order.pickup_selected"
ORDER_EVENT_PICKUP_READY = "order.pickup_ready"
ORDER_EVENT_PICKUP_DONE = "order.pickup_done"
ORDER_EVENT_PICKUP_EXPIRED = "order.pickup_expired"

ORDER_EVENT_TYPE = (
    (ORDER_EVENT_CREATED, "Заказ создан"),
    (ORDER_EVENT_COLLECTING, "Заказ передан в сборку"),
    (ORDER_EVENT_CANCELED, "Заказ отменён"),
    (ORDER_EVENT_REFUNDED, "Возврат средств"),
    (ORDER_EVENT_SYNC_FAILED, "Ошибка синхронизации с 1С"),
    (ORDER_EVENT_PICKUP_SELECTED, "Выбран самовывоз"),
    (ORDER_EVENT_PICKUP_READY, "Готов к выдаче"),
    (ORDER_EVENT_PICKUP_DONE, "Выдан в магазине"),
    (ORDER_EVENT_PICKUP_EXPIRED, "Срок хранения истёк"),
)

OUTBOX_PENDING = "pending"
OUTBOX_SENT = "sent"
OUTBOX_FAILED = "failed"
OUTBOX_RECORDED = "recorded"

OUTBOX_STATUS = (
    (OUTBOX_PENDING, "В очереди"),
    (OUTBOX_SENT, "Отправлено"),
    (OUTBOX_FAILED, "Ошибка"),
    (OUTBOX_RECORDED, "Только запись"),
)

PUBLISH_STATUS_DRAFT = "draft"
PUBLISH_STATUS_REVIEW = "review"
PUBLISH_STATUS_PUBLISHED = "published"

PUBLISH_STATUS = (
    (PUBLISH_STATUS_DRAFT, "Черновик"),
    (PUBLISH_STATUS_REVIEW, "На проверке"),
    (PUBLISH_STATUS_PUBLISHED, "Опубликован"),
)
