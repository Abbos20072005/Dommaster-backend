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
