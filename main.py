import os
import traceback
import logging
from urllib.request import urlopen
from bs4 import BeautifulSoup
from sqlalchemy import create_engine, text
import pandas as pd
from settings import settings as config
import datetime
import re

# Create the log file if it doesn't exist
if not os.path.exists(config.log_file):
    with open(config.log_file, "w"):
        pass

# Configure the logging settings
logging.basicConfig(
    filename=config.log_file, level=logging.INFO, format=config.log_format
)

# now = datetime.now()
# today_date = datetime.strftime(now, format="%Y-%m-%d")


def format_df_numbers(df: pd.DataFrame, col_list: list):
    dfc = df.copy()
    for i in col_list:
        dfc[i] = dfc[i].str.replace(",", ".", regex=False)
        dfc[i] = pd.to_numeric(dfc[i])
    return dfc


def get_barra(txt: str):
    data = re.search(r"\d{2}/\d{2}/\d{4} \d{1,2}:\d{2}", txt).group()
    status = "undefined"
    if "abert" in txt.lower():
        status = "Abriu"
    if "fechad" in txt.lower():
        status = "Fechou"

    return {
        "data": datetime.datetime.strptime(data, "%d/%m/%Y %H:%M"),
        "status": status,
    }


try:
    with urlopen(config.site_praticagem) as response:
        soup = BeautifulSoup(response, "html.parser")

        start_point = soup.find("span", string=f"PORTO DO AÇU - T1")

        table_ship = start_point.parent.parent.parent.parent.find_all(
            "table",
            recursive=False,  # recursive is used to get only the tables direct inside the element
        )[2]

        barra = start_point.parent.find("div").find("div").get_text(strip=True)

        data = []
        header = [cell.get_text(strip=True) for cell in table_ship.find_all("th")]

        header.append(header[len(header) - 1])

        for row in table_ship.find_all("tr"):
            row_data = [cell.get_text(strip=True) for cell in row.find_all("td")]
            data.append(row_data)

    # Create a Pandas DataFrame from the extracted data
    df = pd.DataFrame(data)

    df.columns = header
    df.dropna(subset=["POB"], inplace=True)

    df["Barra"] = barra

    info = get_barra(barra)

    df = df.loc[:, ~df.columns.duplicated()]

    year_now = datetime.datetime.now().year

    df["POB"] = str(year_now) + "/" + df["POB"]

    df["POB"] = pd.to_datetime(df["POB"], format="%Y/%d/%m %H:%M")

    list_numeric_cols = ["CALADO", "LOA", "BOCA", "GT", "DWT"]

    df = df[
        (df["MANOBRA"].str.lower() == "entrada")
        | (df["MANOBRA"].str.lower() == "saída")
        | (df["MANOBRA"].str.lower() == "saida")
    ]

    df = format_df_numbers(df, list_numeric_cols)

    if config.db_endpoint:
        db_url = f"postgresql://{config.db_user}:{config.db_pass}@{config.db_host}/{config.db_database}?sslmode=require&options=endpoint%3D{config.db_endpoint}"
    else:
        db_url = f"postgresql://{config.db_user}:{config.db_pass}@{config.db_host}/{config.db_database}?sslmode=require"

    engine = create_engine(db_url)
    con = engine.connect()

    # Manobras da Praticagem
    con.execute(text(f"TRUNCATE TABLE {config.db_table}"))
    df.to_sql(config.db_table, engine, if_exists="replace", index=False)

    # Criação da tabela de barra caso não exista
    con.execute(
        text(
            """
        CREATE TABLE IF NOT EXISTS status_barra (
            ID SERIAL PRIMARY KEY,
            datetime TIMESTAMP,
            status VARCHAR(40)
        )
    """
        )
    )

    # Selecionando a ultima data para comparar se vai inserir um novo registro
    status_f_db = con.execute(
        text("SELECT * FROM status_barra ORDER BY ID DESC LIMIT 1")
    ).fetchone()

    # Função para reduzi o codigo
    def insert_status(datetime, status):
        insert_query = text(
            """
            INSERT INTO status_barra (datetime, status) VALUES (:datetime, :status)
        """
        )
        con.execute(insert_query, {"datetime": datetime, "status": status})

    if status_f_db == None:
        insert_status(info["data"], info["status"])
    else:
        if status_f_db[1] != info["data"]:
            insert_status(info["data"], info["status"])
        else:
            print("Já existe um registro igual no banco")

    engine.dispose()

    logging.info(f"Executado com sucesso!")

    print("Concluido com sucesso!")


except Exception as e:
    print(e)
    traceback.print_exc()
    logging.error(f"message: {e}")
