import sqlite3
import json
import os

DB_FILE = os.path.join('db-server', 'kiosk.db')

def get_db_connection():
    """Establishes a connection to the SQLite database."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row  # This allows accessing columns by name
    return conn

def get_all_places(lang='ko'):
    """
    Fetches all places with their i18n names and cover images.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = """
        SELECT
            p.place_id,
            p.type,
            p.category,
            p.lat,
            p.lng,
            p.tags_json,
            p.priority_score,
            pi.name,
            pi.short_desc,
            img.url as cover_image_url
        FROM
            places p
        JOIN
            place_i18n pi ON p.place_id = pi.place_id
        LEFT JOIN
            place_images img ON p.cover_image_id = img.image_id
        WHERE
            pi.lang = ?
        ORDER BY
            p.priority_score DESC, p.place_id ASC
    """
    
    cursor.execute(query, (lang,))
    places = [dict(row) for row in cursor.fetchall()]
    
    # Parse the JSON string for tags
    for place in places:
        if place['tags_json']:
            place['tags'] = json.loads(place['tags_json'])
        else:
            place['tags'] = []
            
    conn.close()
    return places

def get_place_details(place_id, lang='ko'):
    """
    Fetches detailed information for a single place, including all its images.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get main place info
    details_query = """
        SELECT
            p.place_id,
            p.type,
            p.category,
            pi.name,
            pi.short_desc,
            pi.address_text,
            pi.hours_text
        FROM
            places p
        JOIN
            place_i18n pi ON p.place_id = pi.place_id
        WHERE
            p.place_id = ? AND pi.lang = ?
    """
    cursor.execute(details_query, (place_id, lang))
    details = dict(cursor.fetchone())

    # Get all images for the place
    images_query = """
        SELECT
            image_id,
            kind,
            url
        FROM
            place_images
        WHERE
            place_id = ?
        ORDER BY
            is_primary DESC, sort_order ASC
    """
    cursor.execute(images_query, (place_id,))
    images = [dict(row) for row in cursor.fetchall()]

    details['images'] = images
    conn.close()
    
    return details

if __name__ == '__main__':
    # For testing the module
    print("--- Testing get_all_places() ---")
    all_places = get_all_places()
    if all_places:
        print(f"Found {len(all_places)} places.")
        print("First place:", all_places[0])
    else:
        print("No places found.")
        
    print("\n--- Testing get_place_details(1001) ---")
    place_details = get_place_details(1001)
    if place_details:
        print(f"Details for place 1001: {place_details}")
    else:
        print("Place with ID 1001 not found.")
