BASE_REPAIR_BUDGET = 250.0

NORMAL_CUT_REFUND_RATE = 0.0
FOREIGN_TRANSFER_REFUND_RATE = 0.50

UNLIMITED_CUTS = True


SINGLE_PLAYER_BUDGET_CAP = {
    "P": 0.20,
    "D": 0.30,
    "C": 0.45,
    "A": 0.65,
}


def foreign_transfer_refund(
    purchase_cost,
):
    return (
        float(purchase_cost)
        * FOREIGN_TRANSFER_REFUND_RATE
    )
