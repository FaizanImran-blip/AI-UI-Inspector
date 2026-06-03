import json
import xml.etree.ElementTree as ET
import os


def make_custom_ui_xml(
    parent_json_path="assets/parent_groups.json",
    output_xml_path="assets/custom_uiautomation.xml",
):
    with open(parent_json_path, "r") as f:
        parents = json.load(f)

    root = ET.Element("screen")

    for i, p in enumerate(parents):
        parent_node = ET.SubElement(root, "node")
        parent_node.set("id", str(i))
        parent_node.set("type", p.get("type", "parent"))
        parent_node.set("x", str(p["x"]))
        parent_node.set("y", str(p["y"]))
        parent_node.set("width", str(p["width"]))
        parent_node.set("height", str(p["height"]))
        parent_node.set("children_count", str(p.get("children_count", 0)))

        for j, c in enumerate(p.get("children", [])):
            child_node = ET.SubElement(parent_node, "child")
            child_node.set("id", f"{i}_{j}")
            child_node.set("type", c.get("type", "element"))
            child_node.set("x", str(c["x"]))
            child_node.set("y", str(c["y"]))
            child_node.set("width", str(c["width"]))
            child_node.set("height", str(c["height"]))
            child_node.set(
                "bounds",
                f'[{c["x"]},{c["y"]}][{c["x"]+c["width"]},{c["y"]+c["height"]}]',
            )
            child_node.set("clickable", str(c.get("clickable", False)).lower())
            child_node.set("text", c.get("text", ""))

    os.makedirs(os.path.dirname(output_xml_path), exist_ok=True)

    tree = ET.ElementTree(root)
    tree.write(output_xml_path, encoding="utf-8", xml_declaration=True)

    print("Custom UI XML saved:", output_xml_path)
