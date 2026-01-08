import sqlite3
import json
import os

DB_FILE = 'kiosk.db'
SCHEMA_FILE = 'local.sql'
DATA_FILE = 'kiosk_data.json'

def setup_database():
    """
    Initializes the SQLite database by executing the schema and populating it
    with data from the JSON file.
    """
    # 1. Delete old DB file if it exists
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
        print(f"Removed old database file: {DB_FILE}")

    # 2. Connect to the database (this will create the file)
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        print(f"Successfully connected to {DB_FILE}")
    except sqlite3.Error as e:
        print(f"Error connecting to database: {e}")
        return

    # 3. Read and execute the schema
    try:
        with open(SCHEMA_FILE, 'r', encoding='utf-8') as f:
            schema_sql = f.read()
        cursor.executescript(schema_sql)
        print(f"Successfully executed schema from {SCHEMA_FILE}")
    except FileNotFoundError:
        print(f"Error: Schema file not found at {SCHEMA_FILE}")
        conn.close()
        return
    except sqlite3.Error as e:
        print(f"Error executing schema: {e}")
        conn.close()
        return
        
    # 4. Load the data from JSON
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Data file not found at {DATA_FILE}")
        conn.close()
        return

    # 5. Insert data into tables
    try:
        print("Inserting data...")
        
        # Insert kiosks (with name from kiosk_i18n)
        if 'kiosk' in data and 'kiosk_i18n' in data:
            kiosk_names = {item['kiosk_id']: item['name'] for item in data['kiosk_i18n'] if item['lang'] == 'ko'}
            for kiosk in data['kiosk']:
                cursor.execute(
                    "INSERT INTO kiosks (kiosk_id, name, lat, lng, radius_m, default_lang) VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        kiosk['kiosk_id'],
                        kiosk_names.get(kiosk['kiosk_id'], "Default Name"), # Use Korean name as default
                        kiosk['lat'],
                        kiosk['lng'],
                        kiosk['radius_m'],
                        kiosk['default_lang']
                    )
                )

        # Insert places
        if 'places' in data:
            for place in data['places']:
                cursor.execute(
                    """INSERT INTO places (place_id, type, category, lat, lng, tags_json, is_vegan, priority_score, cover_image_id) 
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        place['place_id'],
                        place['type'],
                        place['category'],
                        place['lat'],
                        place['lng'],
                        json.dumps(place.get('tags', [])), # Convert list to JSON string
                        place.get('is_vegan'),
                        place['priority_score'],
                        place.get('cover_image_id')
                    )
                )
        
        # Insert place_i18n
        if 'place_i18n' in data:
            for item in data['place_i18n']:
                cursor.execute(
                    "INSERT INTO place_i18n (place_id, lang, name, short_desc, address_text, hours_text) VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        item['place_id'],
                        item['lang'],
                        item['name'],
                        item['short_desc'],
                        item['address_text'],
                        item['hours_text']
                    )
                )

        # Insert place_images
        if 'place_images' in data:
            for image in data['place_images']:
                cursor.execute(
                    """INSERT INTO place_images (image_id, place_id, kind, url, storage_key, mime, width, height, bytes_len, is_primary, sort_order)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        image['image_id'],
                        image['place_id'],
                        image['kind'],
                        image['url'],
                        image.get('storage_key'),
                        image['mime'],
                        image.get('width'),
                        image.get('height'),
                        image.get('bytes_len'),
                        image['is_primary'],
                        image['sort_order']
                    )
                )
        
        # Insert local_meta
        if 'dataset_version' in data:
            cursor.execute("INSERT INTO local_meta (key, value) VALUES (?, ?)", ('dataset_version', str(data['dataset_version'])))

        conn.commit()
        print("Data insertion complete.")

    except sqlite3.Error as e:
        print(f"Error inserting data: {e}")
        conn.rollback()
    finally:
        conn.close()
        print("Database connection closed.")


if __name__ == '__main__':
    setup_database()
