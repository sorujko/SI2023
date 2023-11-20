from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import psycopg2
from collections import defaultdict

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# MySQL Connection setup
db = psycopg2.connect(
    host="localhost",
    user="juro",
    password="dvYbk1fGqez6FZgqtbOmCLIJs5k2Hfjt",
    database="ubytovanie_g517",
    port = '5432'
)
cursor = db.cursor()

@app.get("/")
async def read_form(request: Request):
    return templates.TemplateResponse("linky.html", {"request": request})

@app.get("/prihlaska")
async def read_form(request: Request):
    return templates.TemplateResponse("form.html", {"request": request})

@app.post("/submit_form", response_class=HTMLResponse)
async def submit_form(
    request: Request,
    ID: str = Form(...),
    priemer: float = Form(...),
    vzdialenost: int = Form(...),
    intrak: str = Form(...)
):
    try:
        # Insert data into the MySQL database
        insert_query = "INSERT INTO prihlasky (ID, priemer, vzdialenost, intrak_pozadovany) VALUES (%s, %s, %s, %s)"
        insert_values = (ID, priemer, vzdialenost, intrak)
        cursor.execute(insert_query, insert_values)
        db.commit()

        return templates.TemplateResponse("success.html", {"request": request})
    except psycopg2.Error as err:
        return templates.TemplateResponse("error.html", {"request": request, "error": err})

@app.get("/podane_prihlasky", response_class=HTMLResponse)
async def podane_prihlasky(request: Request):
    try:
        # Fetch data from the MySQL database
        select_query = "SELECT * FROM prihlasky"
        cursor.execute(select_query)
        results = cursor.fetchall()
        return templates.TemplateResponse("prihlasky_list.html", {"request": request, "results": results})
    except psycopg2.Error as err:
        return templates.TemplateResponse("error.html", {"request": request, "error": err})
    


    

@app.get("/update_prihlaska")
async def uprav_prihlasku(request: Request, ID: str, Priemer: str, Vzdialenost: str, Intrak: str):
    try:
        # Fetch existing IDs from the database
        select_ids_query = "SELECT ID FROM prihlasky"
        cursor.execute(select_ids_query)
        existing_ids = cursor.fetchall()
        # Extracting IDs from the result
        existing_ids = [id[0] for id in existing_ids]

        return templates.TemplateResponse("modify_form.html", {"request": request, "existing_ids": existing_ids, "ID": ID, "Priemer": Priemer, "Vzdialenost": Vzdialenost, "Intrak": Intrak})
    except psycopg2.Error as err:
        return templates.TemplateResponse("error.html", {"request": request, "error": err})




@app.post("/update_form", response_class=HTMLResponse)
async def update_form(
    request: Request,
    ID: str = Form(...),
    priemer: float = Form(...),
    vzdialenost: int = Form(...),
    intrak: str = Form(...)
):
    try:
        # Update data in the MySQL database
        update_query = """
        UPDATE prihlasky
        SET priemer = %s, vzdialenost = %s, intrak_pozadovany = %s
        WHERE ID = %s
        """
        update_values = (priemer, vzdialenost, intrak, ID)
        cursor.execute(update_query, update_values)
        db.commit()

        return templates.TemplateResponse("success.html", {"request": request})
    except psycopg2.Error as err:
        return templates.TemplateResponse("error.html", {"request": request, "error": err})


@app.post("/delete_record", response_class=HTMLResponse)
async def delete_record(request: Request, ID: str = Form(...)):
    try:
        # Delete record from the MySQL database
        delete_query = "DELETE FROM prihlasky WHERE ID = %s"
        delete_values = (ID,)
        cursor.execute(delete_query, delete_values)
        db.commit()

        # Redirect to a success or main page after deletion
        return templates.TemplateResponse("success.html", {"request": request})
    except psycopg2.Error as err:
        return templates.TemplateResponse("error.html", {"request": request, "error": err})


@app.get("/vyhodnotene_prihlasky", response_class=HTMLResponse)
async def vyhodnotene_prihlasky(request: Request):
    try:
        # Truncate the vyhodnotene_prihlasky table
        truncate_query = "TRUNCATE TABLE vyhodnotene_prihlasky"
        cursor.execute(truncate_query)
        
        # Order by body in descending order
        select_query = """
        SELECT ID, intrak_pozadovany, (vzdialenost * 0.5) + 300 - (100 * (priemer - 1)) AS body
        FROM prihlasky
        ORDER BY body DESC
        """
        cursor.execute(select_query)
        results = cursor.fetchall()

        # Given priority list and maximum allocations
        priority_list = ["Prokopa Veľkého 41", "Dolnozemská", "Starohájska 8", "Starohájska 4", "Hroboňova 4", "Vlčie hrdlo"]
        max_allocations = 1

        # Keep track of available slots for each intrak_pozadovany
        available_slots = {intrak: max_allocations for intrak in priority_list}

        for row in results:
            intrak_pozadovany = row[1]
            allocated = False

            if available_slots[intrak_pozadovany] > 0:
                intrak_assigned = intrak_pozadovany
                available_slots[intrak_pozadovany] -= 1
                allocated = True
            else:
                for intrak in priority_list:
                    if available_slots[intrak] > 0:
                        intrak_assigned = intrak
                        available_slots[intrak] -= 1
                        allocated = True
                        break
                
            if not allocated:
                intrak_assigned = "neprideleny internat"

            # Insert into the 'vyhodnotene_prihlasky' table
            insert_query = "INSERT INTO vyhodnotene_prihlasky (ID, intrak_prideleny, body) VALUES (%s, %s, %s)"
            data_to_insert = (row[0], intrak_assigned, row[2])
            cursor.execute(insert_query, data_to_insert)
            db.commit()

        # Fetch data from the vyhodnotene_prihlasky table after the allocation process
        fetch_query = "SELECT * FROM vyhodnotene_prihlasky ORDER BY body DESC"
        cursor.execute(fetch_query)
        results = cursor.fetchall()

        return templates.TemplateResponse("vyhodnotene_prihlasky.html", {"request": request, "results": results})
    except psycopg2.Error as err:
        return templates.TemplateResponse("error.html", {"request": request, "error": err})
