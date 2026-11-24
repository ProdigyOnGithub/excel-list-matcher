import pandas as pd
import difflib

# Need to accomodate for columns which are left empty so need an empty column fallback

class MyntraMatcher:
    def __init__(self, name):
        self.name = name

    def matching(self, raw_dir, output_dir, info):
        id_count = 1
        df = pd.read_excel(raw_dir)

        # Alt names / aliases and fuzzy matching for required raw columns
        column_aliases = {
            "Check": ["Check", "check", "Style Code", "StyleCode", "style_code", "SKU"],
            "Color": ["Color", "Colour", "color", "colour", "Brand Colour"],
            "Size": ["Size", "size", "Standard Size", "Brand Size"],
            "Product name": ["Product name", "Product Name", "product_name", "Title", "Item Name"],
        }

        for canonical_col, aliases in column_aliases.items():
            matched_col = None
            # 1. Exact / case-insensitive match against aliases
            for col in df.columns:
                col_clean = str(col).strip().lower()
                if any(col_clean == a.strip().lower() for a in aliases):
                    matched_col = col
                    break

            # 2. Small fuzzy matching fallback if not matched directly
            if not matched_col:
                for col in df.columns:
                    col_clean = str(col).strip().lower()
                    close = difflib.get_close_matches(col_clean, [a.lower() for a in aliases], n=1, cutoff=0.8)
                    if close:
                        matched_col = col
                        break

            if matched_col:
                if matched_col != canonical_col:
                    df.rename(columns={matched_col: canonical_col}, inplace=True)
            else:
                raise ValueError(f"column {canonical_col} is not present in the raw data, kindly provide it to proceed further")

        # Clean strings
        for c in ["Check", "Color", "Size", "Product name"]:
            df[c] = df[c].fillna("").astype(str).str.strip()

        # Check for optional Supplier code in raw data
        for col in df.columns:
            if str(col).strip().lower() in ["supplier code", "suppliercode", "supplier_code", "vendor code"]:
                df.rename(columns={col: "Supplier code"}, inplace=True)
                break

        # Comprehensive default attributes matching dropship_template.xlsx
        defaults = {
            "brand": "StyleCast",
            "Manufacturer Name and Address with Pincode": "Dongguan YouHuo Fashion Co Ltd, Room 301, Building 1, Zhenkou Pedestrian Street, Humen Town, Dongguan City, Guangdong Province, China - 523911",
            "Packer Name and Address with Pincode": "ENSO LOGIC COMMERCE PRIVATE LIMITED, KH NO 427 GROUND FLOOR VILLAGE MUNDKA, NEAR RANI KHERA ROAD, Delhi - 110041",
            "Importer Name and Address with Pincode": "ENSO LOGIC COMMERCE PRIVATE LIMITED, KH NO 427 GROUND FLOOR VILLAGE MUNDKA, NEAR RANI KHERA ROAD, Delhi - 110041",
            "Country Of Origin": "China",
            "articleType": "Sweaters",
            "is Standard Size present on Label": "Yes",
            "HSN": "61101120",
            "AgeGroup": "Adults-Women",
            "FashionType": "Fashion",
            "Usage": "Casual",
            "Year": "2026",
            "season": "Winter",
            "materialCareDescription": "Hand wash cold, do not tumble dry, dry flat in shade, do not bleach, do not iron directly on print or embellishment.",
            "tags": "women sweater, sweater for women, womens sweater, women sweaters, sweaters for women, womens sweaters, women pullover, pullover for women, womens pullover, women cardigan, cardigan for women, womens cardigan, ladies sweater, women casual sweater, women sweater casual, women party sweater, women sweater party, women everyday sweater, women sweater everyday, women daily wear sweater, women sweater daily wear, women summer sweater, women sweater summer, women winter sweater, women sweater winter, women trendy sweater, women sweater trendy, women stylish sweater, women sweater stylish, women comfortable sweater, women sweater comfortable, women fashion sweater, women sweater fashion, women ethnic sweater, women sweater ethnic, women printed sweater",
            "Fabric": "Polyester",
            "Fabric 2": "Polyester",
            "Pattern": "Solid",
            "Sleeve Length": "Long Sleeves",
            "Neck": "Shirt Collar",
            "Occasion": "Casual",
            "Closure": "Button",
            "Length": "Regular",
            "Type": "Cardigan",
            "Print or Pattern Type": "Solid",
            "Surface Styling": "NA",
            "Wash Care": "Machine Wash",
            "Number of Pockets": "NA",
            "Hemline": "Straight",
            "Body or Garment Size": "To-Fit Denotes Body Measurements in",
            "Knit or Woven": "Knitted",
            "Center Front Open": "Yes",
            "Sustainable": "Regular",
            "Character": "NA",
            "Multipack Set": "NA",
            "Net Quantity Unit": "Piece",
            "Theme": "NA",
            "Trends": "NA",
            "Personalization": "NA",
            "Fit": "Regular Fit",
            "Net Quantity": "1",
            "MRP": 3999,
            "ISP": 1999,
            "start_style_group_id": 168,
            "Supplier code": "29865",
        }
        merged_info = {**defaults, **(info or {})}

        # 1. 3-digit styleGroupId (same for same Check+Color across different sizes, incrementing by 1)
        start_id = int(merged_info.get("start_style_group_id", 168))
        factorized = pd.factorize(pd.MultiIndex.from_frame(df[["Check", "Color"]]))[0] + start_id
        df["styleGroupId"] = [f"{x:03d}" if x < 100 else str(x) for x in factorized]

        # 2. Identifiers & SKU Codes
        df["vendorSkuCode"] = df["Check"].astype(str) + "-" + df["Color"].astype(str) + "-" + df["Size"].astype(str)
        df["SKUCode"] = df["vendorSkuCode"]
        supplier_code = df["Supplier code"].astype(str) if "Supplier code" in df.columns else str(merged_info.get("Supplier code", "29865"))
        df["vendorArticleNumber"] = df["vendorSkuCode"].astype(str) + "-" + supplier_code
        df["vendorArticleName"] = df["Product name"]

        # 3. Sizes & Colours
        df["Brand Size"] = df["Size"]
        df["Standard Size"] = df["Size"]
        df["is Standard Size present on Label"] = merged_info.get("is Standard Size present on Label", "Yes")
        df["Brand Colour (Remarks)"] = df["Color"]
        df["Prominent Colour"] = df["Color"]

        # 4. Pricing (MRP & ISP)
        if "Sales price" in df.columns:
            def calc_isp(val):
                try:
                    p = float(val)
                    return int(round(p * 25 + 924))
                except (ValueError, TypeError):
                    return merged_info.get("ISP", 1999)

            def calc_mrp(isp_val):
                try:
                    return int(isp_val) * 2 + 1
                except (ValueError, TypeError):
                    return merged_info.get("MRP", 3999)

            df["ISP"] = df["Sales price"].apply(calc_isp)
            df["MRP"] = df["ISP"].apply(calc_mrp)
        else:
            df["MRP"] = merged_info.get("MRP", 3999)
            df["ISP"] = merged_info.get("ISP", 1999)

        # 5. Mandatory Sizing Measurements based on dropship_template.xlsx
        size_measurements = {
            "S": {"Bust": 34, "Chest": 34, "Front Length": 24, "Across Shoulder": 14.5, "To Fit Bust": 36, "To Fit Chest": 36, "To Fit Waist": 30, "Waist": 28},
            "M": {"Bust": 36, "Chest": 36, "Front Length": 24.5, "Across Shoulder": 15, "To Fit Bust": 38, "To Fit Chest": 38, "To Fit Waist": 32, "Waist": 30},
            "L": {"Bust": 38, "Chest": 38, "Front Length": 25, "Across Shoulder": 15.5, "To Fit Bust": 40, "To Fit Chest": 40, "To Fit Waist": 34, "Waist": 32},
            "XL": {"Bust": 40, "Chest": 40, "Front Length": 25.5, "Across Shoulder": 16, "To Fit Bust": 42, "To Fit Chest": 42, "To Fit Waist": 36, "Waist": 34},
            "XXL": {"Bust": 42, "Chest": 42, "Front Length": 26, "Across Shoulder": 16.5, "To Fit Bust": 44, "To Fit Chest": 44, "To Fit Waist": 38, "Waist": 36},
        }

        def get_measurement(sz, key):
            s_clean = str(sz).strip().upper()
            return size_measurements.get(s_clean, {}).get(key, "")

        df["Bust ( Inches )"] = df["Size"].apply(lambda s: get_measurement(s, "Bust"))
        df["Chest ( Inches )"] = df["Size"].apply(lambda s: get_measurement(s, "Chest"))
        df["Front Length ( Inches )"] = df["Size"].apply(lambda s: get_measurement(s, "Front Length"))
        df["Across Shoulder ( Inches )"] = df["Size"].apply(lambda s: get_measurement(s, "Across Shoulder"))
        df["To Fit Bust ( Inches )"] = df["Size"].apply(lambda s: get_measurement(s, "To Fit Bust"))
        df["To Fit Chest ( Inches )"] = df["Size"].apply(lambda s: get_measurement(s, "To Fit Chest"))
        df["To Fit Waist ( Inches )"] = df["Size"].apply(lambda s: get_measurement(s, "To Fit Waist"))
        df["Waist ( Inches )"] = df["Size"].apply(lambda s: get_measurement(s, "Waist"))

        # 6. Product Details (joined attributes matching template)
        product_details_default = (
            f"{merged_info['Fabric']}||{merged_info['Pattern']}||{merged_info['Sleeve Length']}||"
            f"{merged_info['Neck']}||{merged_info['Closure']}||{merged_info['Length']}||"
            f"{merged_info['Type']}||{merged_info['Center Front Open']}||{merged_info['Fit']}"
        )
        df["Product Details"] = merged_info.get("Product Details", product_details_default)

        # 7. Images from raw data (img1 to img7, Thumb fallback)
        image_mapping = [
            (1, "Front Image"),
            (2, "Side Image"),
            (3, "Back Image"),
            (4, "Detail Angle"),
            (5, "Look Shot Image"),
            (6, "Additional Image 1"),
            (7, "Additional Image 2"),
        ]
        for idx, img_col in image_mapping:
            raw_img = f"img{idx}"
            if raw_img in df.columns:
                df[img_col] = df[raw_img].fillna("")
            elif idx == 1 and "Thumb" in df.columns:
                df[img_col] = df["Thumb"].fillna("")
            else:
                df[img_col] = ""

        # 8. All other business/catalog attributes from merged_info
        for key in [
            "brand", "Manufacturer Name and Address with Pincode", "Packer Name and Address with Pincode",
            "Importer Name and Address with Pincode", "Country Of Origin", "articleType", "HSN",
            "AgeGroup", "FashionType", "Usage", "Year", "season", "materialCareDescription", "tags",
            "Fabric", "Fabric 2", "Pattern", "Sleeve Length", "Neck", "Occasion", "Closure",
            "Length", "Type", "Print or Pattern Type", "Surface Styling", "Wash Care",
            "Number of Pockets", "Hemline", "Body or Garment Size", "Knit or Woven",
            "Center Front Open", "Sustainable", "Character", "Multipack Set", "Net Quantity Unit",
            "Theme", "Trends", "Personalization", "Fit", "Net Quantity"
        ]:
            df[key] = merged_info.get(key, "")

        # 9. Build output with ALL 90 columns in exact template order
        template_columns = [
            "styleId", "styleGroupId", "vendorSkuCode", "vendorArticleNumber", "vendorArticleName",
            "brand", "Manufacturer Name and Address with Pincode", "Packer Name and Address with Pincode",
            "Importer Name and Address with Pincode", "Country Of Origin", "Country Of Origin2",
            "Country Of Origin3", "Country Of Origin4", "Country Of Origin5", "articleType",
            "Brand Size", "Standard Size", "is Standard Size present on Label", "Brand Colour (Remarks)",
            "GTIN", "HSN", "SKUCode", "MRP", "ISP", "AgeGroup", "Prominent Colour",
            "Second Prominent Colour", "Third Prominent Colour", "FashionType", "Usage", "Year",
            "season", "AI Label", "List View Name", "Product Details", "styleNote",
            "materialCareDescription", "sizeAndFitDescription", "productDisplayName", "tags",
            "addedDate", "Color Variant GroupId", "Fabric", "Fabric 2", "Pattern",
            "Sleeve Length", "Neck", "Occasion", "Closure", "Length", "Type",
            "Print or Pattern Type", "Surface Styling", "Wash Care", "Number of Pockets",
            "Hemline", "Body or Garment Size", "Knit or Woven", "Center Front Open",
            "Sustainable", "Character", "Multipack Set", "Net Quantity Unit", "Theme",
            "Trends", "Personalization", "Fit", "Sleeve Styling",
            "Contact Brand or Retailer for pre-sales product queries", "Collection Name",
            "BIS Expiry Date", "BIS Certificate Image URL", "BIS Certificate Number", "Net Quantity",
            "Bust ( Inches )", "Chest ( Inches )", "Front Length ( Inches )", "Across Shoulder ( Inches )",
            "Sleeve-Length ( Inches )", "To Fit Bust ( Inches )", "To Fit Chest ( Inches )",
            "To Fit Waist ( Inches )", "Waist ( Inches )", "Front Image", "Side Image",
            "Back Image", "Detail Angle", "Look Shot Image", "Additional Image 1", "Additional Image 2"
        ]

        output = pd.DataFrame()
        for col in template_columns:
            if col in df.columns:
                output[col] = df[col]
            else:
                output[col] = merged_info.get(col, "")

        output.to_excel(output_dir, index=False)
        print(f"done: successfully exported {len(output)} rows across {len(template_columns)} template columns to {output_dir}")

if __name__ == "__main__":
    raw_dir = "dropship_raw_data.xlsx"
    output_dir = "final.xlsx"
    info = {
        "brand": "StyleCast", 
        "Manufacturer Name and Address with Pincode": "Dongguan YouHuo Fashion Co Ltd, Room 301, Building 1, Zhenkou Pedestrian Street, Humen Town, Dongguan City, Guangdong Province, China - 523911",
        "Packer Name and Address with Pincode": "ENSO LOGIC COMMERCE PRIVATE LIMITED, KH NO 427 GROUND FLOOR VILLAGE MUNDKA, NEAR RANI KHERA ROAD, Delhi - 110041",
        "Importer Name and Address with Pincode": "ENSO LOGIC COMMERCE PRIVATE LIMITED, KH NO 427 GROUND FLOOR VILLAGE MUNDKA, NEAR RANI KHERA ROAD, Delhi - 110041",
        "Country Of Origin": "China",
        "articleType": "Sweaters",
        "is Standard Size present on Label": "Yes",
        "HSN": "61101120",
        "AgeGroup": "Adults-Women",
        "FashionType": "Fashion",
        "Usage": "Casual",
        "Year": "2026",
        "season": "Winter"
    }
    MyntraMatcher("Arihant").matching(raw_dir, output_dir, info)
    