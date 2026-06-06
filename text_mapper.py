def attach_text_to_ui_boxes(ui_boxes, ocr_boxes):
    for ui_box in ui_boxes:
        texts = []

        for text_box in ocr_boxes:
            if is_inside_text(text_box, ui_box):
                texts.append(text_box["text"])

        ui_box["text"] = " ".join(texts).strip()

    return ui_boxes


def is_inside_text(text_box, ui_box):
    tx1 = text_box["x"]
    ty1 = text_box["y"]
    tx2 = text_box["x"] + text_box["width"]
    ty2 = text_box["y"] + text_box["height"]

    ux1 = ui_box["x"]
    uy1 = ui_box["y"]
    ux2 = ui_box["x"] + ui_box["width"]
    uy2 = ui_box["y"] + ui_box["height"]

    return tx1 >= ux1 and ty1 >= uy1 and tx2 <= ux2 and ty2 <= uy2