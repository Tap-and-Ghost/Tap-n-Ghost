#!/usr/bin/env python
# -*- coding: utf-8 -*-

import usb1 as libusb

name_by_serial = {
    "0529596": "Alpha",
    "0529594": "Bravo",
    "0530032": "Charlie",
    "0529580": "Delta",
    "0529581": "Echo",
    "0529577": "Foxtrot",
    "0530033": "Golf",
    "0529628": "Hotel",
    "0536945": "India",
    "0540161": "Juliet",
    "0540166": "Kilo",
    "0536948": "Lima",
    "0540160": "Mike",
    "0536951": "November",
    "0536949": "Oscar",
    "0540158": "Papa",
    "0572003": "Zulu",
}


class UnregisteredSerialNumberError(Exception):
    pass


def get_name_path_pairs():
    with libusb.USBContext() as usb_ctx:
        devices = usb_ctx.getDeviceList()

        nfc_RWs = []
        for d in devices:
            try:
                if d.getProduct() == u'RC-S380/P':
                    nfc_RWs.append(d)
            except libusb.USBError as e:
                print("[!] libusb Error: " + str(e))
                print("    Device: " + str(d))

        try:
            name_path_pairs = [(
                name_by_serial[dev.getSerialNumber()],
                ":".join(
                    ["usb", str(dev.getBusNumber()),
                     str(dev.getDeviceAddress())]
                )
            ) for dev in nfc_RWs]
        except KeyError as e:
            raise UnregisteredSerialNumberError(e)
    return name_path_pairs


if __name__ == '__main__':
    np = get_name_path_pairs()
    print(np)
