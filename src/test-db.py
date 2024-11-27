import boto3
import pymysql
import os
import sys

SECRET_NAME = "rds!db-3419db02-547f-45a3-b45e-690fb0626b69"
REGION_NAME = "us-east-1"
BUCKET_NAME = "ecommerce-store-images"
CARPETA_S3 = "products/"
RDS_HOST = "ecommerce-db.cdj5i4puctle.us-east-1.rds.amazonaws.com"
RDS_PORT = 3306

def get_secret():
    session = boto3.session.Session()
    client = session.client(service_name="secretsmanager", region_name=REGION_NAME)
    response = client.get_secret_value(SecretId=SECRET_NAME)
    return eval(response['SecretString'])

def get_db_connection(secret, use_db=True):
    return pymysql.connect(
        host=RDS_HOST,
        user=secret["username"],
        password=secret["password"],
        database="ecommerce_db" if use_db else None,
        port=RDS_PORT
    )

def create_database_if_not_exists(secret):
    connection = get_db_connection(secret, use_db=False)
    try:
        with connection.cursor() as cursor:
            cursor.execute("CREATE DATABASE IF NOT EXISTS ecommerce_db;")
    finally:
        connection.close()

def create_table_if_not_exists(secret):
    connection = get_db_connection(secret)
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    price DECIMAL(10, 2) NOT NULL,
                    description TEXT,
                    image_url VARCHAR(255) NOT NULL
                );
            """)
            connection.commit()
    finally:
        connection.close()

def upload_to_s3(file_path):
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"Archivo no encontrado: {file_path}")
    s3 = boto3.client('s3')
    file_name = os.path.basename(file_path)
    s3_key = os.path.join(CARPETA_S3, file_name)
    s3.upload_file(file_path, BUCKET_NAME, s3_key)
    return f"https://{BUCKET_NAME}.s3.{REGION_NAME}.amazonaws.com/{s3_key}"

def fetch_all_products(secret):
    connection = get_db_connection(secret)
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM products;")
            rows = cursor.fetchall()
            return rows
    finally:
        connection.close()

def insert_product_to_db(secret, name, price, description, image_url):
    connection = get_db_connection(secret)
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO products (name, price, description, image_url)
                VALUES (%s, %s, %s, %s);
            """, (name, price, description, image_url))
            connection.commit()
    finally:
        connection.close()

def delete_product(secret, product_id):
    connection = get_db_connection(secret)
    try:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM products WHERE id = %s;", (product_id,))
            connection.commit()
    finally:
        connection.close()

def display_menu():
    print("\nOpciones:")
    print("1. Agregar un producto")
    print("2. Consultar todos los productos")
    print("3. Eliminar un producto")
    print("4. Salir")

def handle_add_product(secret):
    image_path = input("Ruta de la imagen del producto: ")
    name = input("Nombre del producto: ")
    price = float(input("Precio del producto: "))
    description = input("Descripción del producto: ")
    image_url = upload_to_s3(image_path)
    insert_product_to_db(secret, name, price, description, image_url)
    print(f"Producto '{name}' agregado exitosamente.")

def handle_query_products(secret):
    products = fetch_all_products(secret)
    if not products:
        print("No hay productos en la base de datos.")
    else:
        for product in products:
            print(f"ID: {product[0]}, Nombre: {product[1]}, Precio: {product[2]}, Descripción: {product[3]}, Imagen: {product[4]}")

def handle_delete_product(secret):
    product_id = int(input("ID del producto a eliminar: "))
    delete_product(secret, product_id)
    print(f"Producto con ID {product_id} eliminado exitosamente.")

if __name__ == "__main__":
    secret = get_secret()
    create_database_if_not_exists(secret)
    create_table_if_not_exists(secret)

    while True:
        display_menu()
        choice = input("Selecciona una opción: ")
        if choice == "1":
            handle_add_product(secret)
        elif choice == "2":
            handle_query_products(secret)
        elif choice == "3":
            handle_delete_product(secret)
        elif choice == "4":
            print("Saliendo...")
            break
        else:
            print("Opción no válida, intenta de nuevo.")
