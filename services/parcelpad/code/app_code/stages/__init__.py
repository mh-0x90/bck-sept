from .customs import FLOW as customs
from .delivery import FLOW as delivery
from .label import FLOW as label
from .pickup import FLOW as pickup
from .shipment import FLOW as shipment


FLOW_OBJECTS = {
    "shipment": shipment,
    "label": label,
    "pickup": pickup,
    "customs": customs,
    "delivery": delivery,
}
