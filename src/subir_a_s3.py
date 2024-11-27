import boto3
import os
import sys

s3 = boto3.client('s3')
NOMBRE_BUCKET = 'ecommerce-store-images'
CARPETA_S3 = 'uploads/'

for ruta_archivo in sys.argv[1:]:
    if os.path.isfile(ruta_archivo):
        nombre_archivo = os.path.basename(ruta_archivo)
        clave_s3 = os.path.join(CARPETA_S3, nombre_archivo)
        s3.upload_file(ruta_archivo, NOMBRE_BUCKET, clave_s3)
        print(f"Archivo subido: {ruta_archivo} a s3://{NOMBRE_BUCKET}/{clave_s3}")
    else:
        print(f"No es un archivo válido: {ruta_archivo}")
