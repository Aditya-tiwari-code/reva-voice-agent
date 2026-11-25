import os
import re
import csv
import shutil
import pandas as pd
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"

def clean_text(text: str) -> str:
    """Strip, replace multiple whitespace/newlines with single spaces."""
    if not text or pd.isna(text):
        return ""
    text = str(text)
    # Remove control characters and normalize spaces
    text = re.sub(r'[\r\n\t]+', ' ', text)
    text = re.sub(r'\s{2,}', ' ', text)
    return text.strip()

def ingest_all_datasets():
    print("=== REVA DATASET INGESTION ===")
    
    # 1. Load existing base properties.csv (Demo properties 1-40)
    base_csv = DATA_DIR / "properties.csv"
    existing_rows = []
    max_id = 0
    if base_csv.exists():
        backup_csv = DATA_DIR / "properties_demo_backup.csv"
        if not backup_csv.exists():
            shutil.copyfile(base_csv, backup_csv)
            print(f"[INFO] Created backup of original demo data at: {backup_csv.name}")

        with open(base_csv, mode="r", encoding="utf-8", errors="ignore") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    row_id = int(row["id"])
                    if row_id > max_id:
                        max_id = row_id
                except Exception:
                    pass
                existing_rows.append(row)
        print(f"[INFO] Loaded {len(existing_rows)} existing base properties (max_id: {max_id})")

    unified_properties = list(existing_rows)

    # 2. Ingest real_estate_main.csv (Buy properties across Delhi, Gurgaon, Noida, Ghaziabad, Faridabad)
    main_csv = DATA_DIR / "real_estate_main.csv"
    if main_csv.exists():
        print(f"[INFO] Ingesting {main_csv.name}...")
        df_main = pd.read_csv(main_csv)
        added_main = 0

        for _, r in df_main.iterrows():
            name = clean_text(r.get("Name", ""))
            if not name:
                continue

            city = clean_text(r.get("city", "Delhi")).capitalize()
            raw_loc = clean_text(r.get("location", ""))
            loc = raw_loc.strip() if raw_loc else city

            # Price in Lakhs (Price column is in full rupees e.g. 85000000 -> 850.0 Lakhs)
            try:
                price_val = float(r.get("Price", 0))
                price_lakh = round(price_val / 100000.0, 2)
            except Exception:
                continue

            if price_lakh <= 0:
                continue

            # Bedrooms (BHK)
            try:
                bhk = int(r.get("bedroom", 2))
            except Exception:
                bhk = 2

            # Area in sqft
            area = r.get("total_area")
            if pd.isna(area) or float(area) < 100:
                area = r.get("carpet_area_sqft")
            if pd.isna(area) or float(area) < 100:
                area = bhk * 500
            try:
                area_sqft = int(round(float(area)))
            except Exception:
                area_sqft = bhk * 500

            # Property type
            name_lower = name.lower()
            if "villa" in name_lower:
                prop_type = "Villa"
            elif "penthouse" in name_lower:
                prop_type = "Penthouse"
            elif "builder floor" in name_lower or "independent floor" in name_lower:
                prop_type = "Independent Floor"
            elif "house" in name_lower:
                prop_type = "Independent House"
            else:
                prop_type = "Apartment"

            # Amenities & Features
            amenity_parts = []
            parking = clean_text(r.get("parking", ""))
            if parking and parking.lower() != "nan":
                amenity_parts.append(f"Parking: {parking}")
            facing = clean_text(r.get("facing", ""))
            if facing and facing.lower() != "nan":
                amenity_parts.append(f"Facing: {facing}")
            overlooking = clean_text(r.get("overlooking", ""))
            if overlooking and overlooking.lower() != "nan":
                amenity_parts.append(f"Overlooking: {overlooking}")
            status_val = clean_text(r.get("status", "Ready to Move"))
            if not status_val or status_val.lower() == "nan":
                status_val = "Ready to Move"
            amenity_parts.append(f"Status: {status_val}")
            bathrooms = r.get("bathroom")
            if pd.notnull(bathrooms):
                try:
                    amenity_parts.append(f"{int(bathrooms)} Bathrooms")
                except Exception:
                    pass
            amenities = ", ".join(amenity_parts)

            # Description
            desc_parts = [
                f"{bhk} BHK {prop_type} for sale in {loc}, {city}.",
                f"Built-up area of {area_sqft} sqft.",
                f"Offered at ₹{price_lakh:g} Lakh." if price_lakh < 100 else f"Offered at ₹{price_lakh/100:.2f} Crore.",
                f"Availability: {status_val}."
            ]
            if facing and facing.lower() != "nan":
                desc_parts.append(f"Unit is {facing} facing.")
            if overlooking and overlooking.lower() != "nan":
                desc_parts.append(f"Overlooks {overlooking}.")
            desc = " ".join(desc_parts)

            max_id += 1
            unified_properties.append({
                "id": max_id,
                "title": name,
                "location": loc,
                "city": city,
                "price_lakh": price_lakh,
                "property_type": prop_type,
                "bhk": bhk,
                "area_sqft": area_sqft,
                "transaction_type": "buy",
                "amenities": amenities,
                "availability": status_val,
                "description": desc
            })
            added_main += 1

        print(f"[SUCCESS] Added {added_main} buy properties from {main_csv.name}")

    # 3. Ingest Indian_housing_Delhi_data.csv (Rent properties in Delhi)
    delhi_csv = DATA_DIR / "Indian_housing_Delhi_data.csv"
    if delhi_csv.exists():
        print(f"[INFO] Ingesting {delhi_csv.name}...")
        df_delhi = pd.read_csv(delhi_csv)
        # Deduplicate
        df_delhi = df_delhi.drop_duplicates(subset=["house_type", "house_size", "location", "price", "Status"])
        added_delhi = 0

        for _, r in df_delhi.iterrows():
            ht = clean_text(r.get("house_type", "Apartment"))
            loc = clean_text(r.get("location", "Delhi"))
            if not loc:
                loc = "Delhi"

            # Rent price: price column is monthly rent in rupees e.g. 22000 -> 22.0 in price_lakh (thousands)
            try:
                monthly_rent = float(r.get("price", 0))
                price_lakh = round(monthly_rent / 1000.0, 2)
            except Exception:
                continue

            if price_lakh <= 0:
                continue

            # BHK extraction from house_type
            bhk_m = re.search(r'(\d+)\s*BHK', ht, re.IGNORECASE)
            if bhk_m:
                bhk = int(bhk_m.group(1))
            elif "1 rk" in ht.lower() or "studio" in ht.lower():
                bhk = 1
            else:
                bhk = 1

            # Property type
            ht_lower = ht.lower()
            if "studio" in ht_lower or "1 rk" in ht_lower:
                prop_type = "Studio Apartment"
            elif "villa" in ht_lower:
                prop_type = "Villa"
            elif "builder floor" in ht_lower or "independent floor" in ht_lower:
                prop_type = "Independent Floor"
            elif "house" in ht_lower:
                prop_type = "Independent House"
            else:
                prop_type = "Apartment"

            # Area sqft extraction (e.g. '1,020 sq ft')
            hs = clean_text(r.get("house_size", ""))
            size_m = re.search(r'([\d,]+)', hs)
            if size_m:
                try:
                    area_sqft = int(size_m.group(1).replace(",", ""))
                except Exception:
                    area_sqft = bhk * 500
            else:
                area_sqft = bhk * 500

            # Furnishing and amenities
            furnishing = clean_text(r.get("Status", "Semi-Furnished"))
            if not furnishing or furnishing.lower() == "nan":
                furnishing = "Semi-Furnished"

            amenity_parts = [furnishing]
            baths = r.get("numBathrooms")
            if pd.notnull(baths):
                try:
                    amenity_parts.append(f"{int(baths)} Bathrooms")
                except Exception:
                    pass
            balcs = r.get("numBalconies")
            if pd.notnull(balcs):
                try:
                    amenity_parts.append(f"{int(balcs)} Balconies")
                except Exception:
                    pass
            sec = clean_text(r.get("SecurityDeposit", ""))
            if sec and sec.lower() not in ["nan", "no deposit"]:
                amenity_parts.append(f"Deposit: Rs {sec}")
            amenities = ", ".join(amenity_parts)

            title = f"{bhk} BHK {prop_type} in {loc}, Delhi"
            raw_desc = clean_text(r.get("description", ""))
            if len(raw_desc) > 350:
                raw_desc = raw_desc[:350].rsplit(" ", 1)[0] + "..."
            
            if not raw_desc:
                raw_desc = f"{bhk} BHK {prop_type} available for rent in {loc}, Delhi. Monthly rent ₹{int(monthly_rent):,}/month. {furnishing} with modern amenities."

            max_id += 1
            unified_properties.append({
                "id": max_id,
                "title": title,
                "location": loc,
                "city": "Delhi",
                "price_lakh": price_lakh,
                "property_type": prop_type,
                "bhk": bhk,
                "area_sqft": area_sqft,
                "transaction_type": "rent",
                "amenities": amenities,
                "availability": "Ready to Move",
                "description": raw_desc
            })
            added_delhi += 1

        print(f"[SUCCESS] Added {added_delhi} rental properties from {delhi_csv.name}")

    # 4. Save unified master dataset to properties.csv
    fieldnames = [
        "id", "title", "location", "city", "price_lakh", "property_type",
        "bhk", "area_sqft", "transaction_type", "amenities", "availability", "description"
    ]
    with open(base_csv, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(unified_properties)

    print(f"\n[DONE] Successfully saved unified dataset with {len(unified_properties)} properties into {base_csv}")
    return len(unified_properties)

if __name__ == "__main__":
    ingest_all_datasets()
