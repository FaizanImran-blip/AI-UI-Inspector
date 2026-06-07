import os
import json
import xml.etree.ElementTree as ET



def parse_bounds(bounds):
    # "[49,278][582,367]" -> x,y,width,height
    bounds = bounds.replace("[", "").replace("]", ",")
    nums = [int(n) for n in bounds.split(",") if n.strip()]

    x1, y1, x2, y2 = nums
    return {
        "x": x1,
        "y": y1,
        "width": x2 - x1,
        "height": y2 - y1,
        "bounds": [x1, y1, x2, y2],
    }


def parse_ui_xml(input_xml="ui.xml", output_json="assets/xml/inspector_output.json"):
    os.makedirs("assets/xml", exist_ok=True)

    tree = ET.parse(input_xml)
    root = tree.getroot()

    nodes = []

    for node in root.iter("node"):
        bounds_text = node.attrib.get("bounds", "")

        if not bounds_text:
            continue

        box = parse_bounds(bounds_text)

        item = {
            "text": node.attrib.get("text", ""),
            "content_desc": node.attrib.get("content-desc", ""),
            "resource_id": node.attrib.get("resource-id", ""),
            "class": node.attrib.get("class", ""),
            "package": node.attrib.get("package", ""),
            "clickable": node.attrib.get("clickable", "false") == "true",
            "enabled": node.attrib.get("enabled", "false") == "true",
            "focusable": node.attrib.get("focusable", "false") == "true",
            **box,
        }

        # empty useless full-screen nodes skip
        if (
            item["text"] == ""
            and item["content_desc"] == ""
            and item["resource_id"] == ""
        ):
            continue

        nodes.append(item)

    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(nodes, f, indent=4, ensure_ascii=False)

    print("XML reading done")
    print("Bounds parsing done")
    print("Saved:", output_json)
    print("Total nodes:", len(nodes))


if __name__ == "__main__":
    parse_ui_xml(
        input_xml="assets/xml/ui.xml", output_json="assets/xml/inspector_output.json"
    )
