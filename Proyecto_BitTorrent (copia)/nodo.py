import sys
import os
import time
import threading
import json
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import math  # <--- IMPORTANTE: Necesario para calcular chunks

import grpc
from concurrent import futures

# Importamos los stubs generados
import bittorrent_pb2
import bittorrent_pb2_grpc
import socket

# --- CONFIGURACIÓN ---
CHUNK_SIZE = 64 * 1024  # 64KB por pedazo
# Ajusta esto a la IP de la máquina que corre el tracker si es diferente
TRACKER_HOST = 'localhost' 
TRACKER_PORT = '50051'

def obtener_mi_ip_real():
    """Detecta la IP de la computadora en la red"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

class P2PServicer(bittorrent_pb2_grpc.P2PServiceServicer):
    """
    Esta clase maneja las peticiones de OTROS nodos que quieren descargar
    archivos de MI computadora.
    """
    def __init__(self, directorio_nodo):
        self.directorio = directorio_nodo

    def SolicitarChunk(self, request, context):
        archivo_path = os.path.join(self.directorio, request.nombre_archivo)
        indice = request.indice_chunk
        
        # Verificar si tenemos el archivo
        if not os.path.exists(archivo_path):
            return bittorrent_pb2.DataChunk(encontrado=False, datos=b'', indice_chunk=indice)
        
        try:
            with open(archivo_path, 'rb') as f:
                # Nos movemos al byte exacto donde empieza el chunk
                f.seek(indice * CHUNK_SIZE)
                # Leemos solo el tamaño del chunk
                data = f.read(CHUNK_SIZE)
                
                return bittorrent_pb2.DataChunk(
                    encontrado=True,
                    datos=data,
                    indice_chunk=indice
                )
        except Exception as e:
            print(f"Error leyendo archivo: {e}")
            return bittorrent_pb2.DataChunk(encontrado=False, datos=b'', indice_chunk=indice)

    # --- ESTA ES LA FUNCIÓN QUE TE FALTABA O ESTABA MAL PUESTA ---
    def ObtenerInfoArchivo(self, request, context):
        # --- CORRECCIÓN: Usamos request.nombre_archivo (como dice el proto) ---
        nombre_buscado = request.nombre_archivo 
        
        full_path = os.path.join(self.directorio, nombre_buscado)
        
        if not os.path.exists(full_path):
            return bittorrent_pb2.InfoArchivo(existe=False, tamano_bytes=0, total_chunks=0)
            
        size = os.path.getsize(full_path)
        # Calculamos cuántos chunks caben
        total_chunks = math.ceil(size / CHUNK_SIZE)
        
        return bittorrent_pb2.InfoArchivo(
            nombre=nombre_buscado, # Aquí sí se usa 'nombre' porque es el mensaje de respuesta
            tamano_bytes=size,
            total_chunks=total_chunks,
            existe=True
        )

class NodoGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.mi_ip = obtener_mi_ip_real() 
        self.title(f"Nodo BitTorrent - IP: {self.mi_ip}")
        self.geometry("700x500")
        
        # Variables de estado
        self.mi_puerto = ""
        self.mi_carpeta = ""
        self.archivos_locales = []
        
        self.crear_interfaz()
        
    def crear_interfaz(self):
        # --- SECCIÓN DE CONEXIÓN ---
        frame_conn = tk.LabelFrame(self, text="Configuración del Nodo", padx=10, pady=10)
        frame_conn.pack(fill="x", padx=10, pady=5)
        
        tk.Label(frame_conn, text="Mi Puerto:").pack(side=tk.LEFT)
        self.ent_puerto = tk.Entry(frame_conn, width=10)
        self.ent_puerto.pack(side=tk.LEFT, padx=5)
        
        self.btn_conectar = tk.Button(frame_conn, text="Iniciar Nodo y Conectar a Tracker", command=self.iniciar_nodo)
        self.btn_conectar.pack(side=tk.LEFT, padx=10)
        
        # --- SECCIÓN DE DESCARGAS ---
        frame_download = tk.LabelFrame(self, text="Descargar Archivo", padx=10, pady=10)
        frame_download.pack(fill="x", padx=10, pady=5)
        
        tk.Label(frame_download, text="Nombre Archivo:").pack(side=tk.LEFT)
        self.ent_archivo = tk.Entry(frame_download, width=30)
        self.ent_archivo.pack(side=tk.LEFT, padx=5)
        
        self.btn_buscar = tk.Button(frame_download, text="Descargar", command=self.buscar_y_descargar)
        self.btn_buscar.pack(side=tk.LEFT, padx=10)
        
        # --- LOG ---
        self.log_area = scrolledtext.ScrolledText(self, height=15)
        self.log_area.pack(fill="both", expand=True, padx=10, pady=10)
        
    def log(self, mensaje):
        self.log_area.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] {mensaje}\n")
        self.log_area.see(tk.END)

    def iniciar_nodo(self):
        puerto = self.ent_puerto.get()
        if not puerto.isdigit():
            messagebox.showerror("Error", "El puerto debe ser un número")
            return
            
        self.mi_puerto = puerto
        
        # Crear carpeta
        self.mi_carpeta = f"archivos_nodo_{puerto}"
        if not os.path.exists(self.mi_carpeta):
            os.makedirs(self.mi_carpeta)
            self.log(f"Carpeta creada: {self.mi_carpeta} (Pon tus archivos aquí)")
        else:
            self.log(f"Usando carpeta existente: {self.mi_carpeta}")
            
        self.archivos_locales = os.listdir(self.mi_carpeta)
        self.log(f"Archivos encontrados: {self.archivos_locales}")
        
        # Iniciar Servidor P2P
        self.server_thread = threading.Thread(target=self.servir_p2p, daemon=True)
        self.server_thread.start()
        
        # Registrar en Tracker
        self.registrar_en_tracker()
        
        self.btn_conectar.config(state=tk.DISABLED)
        self.ent_puerto.config(state=tk.DISABLED)

    def servir_p2p(self):
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        bittorrent_pb2_grpc.add_P2PServiceServicer_to_server(P2PServicer(self.mi_carpeta), server)
        server.add_insecure_port(f'[::]:{self.mi_puerto}')
        self.log(f"Servidor P2P escuchando en puerto {self.mi_puerto}...")
        server.start()
        server.wait_for_termination()

    def registrar_en_tracker(self):
        try:
            with grpc.insecure_channel(f'{TRACKER_HOST}:{TRACKER_PORT}') as channel:
                stub = bittorrent_pb2_grpc.TrackerServiceStub(channel)
                info = bittorrent_pb2.InfoNodo(
                    ip_puerto=f"{self.mi_ip}:{self.mi_puerto}",
                    archivos=self.archivos_locales
                )
                response = stub.RegistrarNodo(info)
                if response.exito:
                    self.log("Exito: Registrado en el Tracker")
                else:
                    self.log(f"Error del Tracker: {response.mensaje}")
        except Exception as e:
            self.log(f"No se pudo conectar al Tracker: {e}")

    def buscar_y_descargar(self):
        nombre_archivo = self.ent_archivo.get()
        if not nombre_archivo: return
        threading.Thread(target=self._logica_descarga, args=(nombre_archivo,)).start()

    def _logica_descarga(self, nombre_archivo):
        self.log(f"--- Iniciando protocolo BitTorrent para: {nombre_archivo} ---")
        
        # 1. Consultar Tracker
        peers = []
        try:
            with grpc.insecure_channel(f'{TRACKER_HOST}:{TRACKER_PORT}') as channel:
                stub = bittorrent_pb2_grpc.TrackerServiceStub(channel)
                resp = stub.BuscarArchivo(bittorrent_pb2.BusquedaArchivo(nombre_archivo=nombre_archivo))
                peers = resp.peers_con_archivo
        except Exception as e:
            self.log(f"Error Tracker: {e}")
            return

        mis_datos = f"{self.mi_ip}:{self.mi_puerto}"
        # Filtrar para no descargarse a sí mismo
        peers = [p for p in peers if str(self.mi_puerto) not in p]
        
        if not peers:
            self.log("Nadie tiene este archivo.")
            return

        self.log(f"Swarm encontrado: {len(peers)} peers.")
        
        # 2. Obtener metadatos
        total_chunks = self._obtener_numero_chunks(peers[0], nombre_archivo)
        if total_chunks == 0:
            return
            
        # --- LÓGICA DE RESUME (TOLERANCIA A FALLOS) ---
        ruta_destino = os.path.join(self.mi_carpeta, nombre_archivo)
        ruta_progreso = ruta_destino + ".progress" # Archivo auxiliar .json
        
        chunks_descargados = set() # Usamos un conjunto para no repetir
        
        # Si existe un archivo de progreso, lo cargamos
        if os.path.exists(ruta_progreso):
            try:
                with open(ruta_progreso, 'r') as f:
                    lista_guardada = json.load(f)
                    chunks_descargados = set(lista_guardada)
                self.log(f"¡RECUPERANDO ESTADO! Ya tienes {len(chunks_descargados)} chunks descargados.")
            except:
                pass # Si falla, empezamos de cero

        if not os.path.exists(ruta_destino):
            with open(ruta_destino, 'wb') as f:
                pass 

        # 3. Descarga Concurrente (Saltando lo que ya tenemos)
        with futures.ThreadPoolExecutor(max_workers=len(peers) * 2) as executor:
            tareas = {} # Diccionario {future: indice_chunk}
            
            for i in range(total_chunks):
                if i in chunks_descargados:
                    continue # ¡SALTAR ESTE CHUNK SI YA LO TENEMOS!
                
                peer_asignado = peers[i % len(peers)]
                tarea = executor.submit(self._descargar_un_chunk, peer_asignado, nombre_archivo, i)
                tareas[tarea] = i
            
            if not tareas:
                self.log("El archivo ya estaba completo. ¡Nada que descargar!")
            
            # Procesar conforme terminan
            for futuro in futures.as_completed(tareas):
                indice = tareas[futuro]
                resultado = futuro.result()
                
                if resultado:
                    chunks_descargados.add(indice)
                    
                    # GUARDAR PROGRESO EN DISCO (Para tolerancia a fallos)
                    # Guardamos cada vez (o podrías guardar cada X chunks)
                    with open(ruta_progreso, 'w') as f:
                        json.dump(list(chunks_descargados), f)
                    
                    # Regla del 20%
                    progreso = (len(chunks_descargados) / total_chunks) * 100
                    if progreso > 20 and nombre_archivo not in self.archivos_locales:
                         self.log(f"Progreso: {progreso:.1f}% - Avisando al Tracker...")
                         self.archivos_locales.append(nombre_archivo)
                         self.registrar_en_tracker()

        if len(chunks_descargados) == total_chunks:
            self.log(f"--- DESCARGA COMPLETADA AL 100% ---")
            # Borramos el archivo de progreso porque ya acabamos
            if os.path.exists(ruta_progreso):
                os.remove(ruta_progreso)
                
            if nombre_archivo not in self.archivos_locales:
                self.archivos_locales.append(nombre_archivo)
            self.registrar_en_tracker()
            messagebox.showinfo("Éxito", f"Archivo {nombre_archivo} completado.")

    def _obtener_numero_chunks(self, peer_address, nombre_archivo):
        try:
            # Corrección para manejo de IPs locales vs reales
            if "localhost" in peer_address:
                address = peer_address
            else:
                address = peer_address # Asumimos que viene correcto del tracker
                
            with grpc.insecure_channel(address) as channel:
                stub = bittorrent_pb2_grpc.P2PServiceStub(channel)
                # Llamada al nuevo RPC
                info = stub.ObtenerInfoArchivo(bittorrent_pb2.BusquedaArchivo(nombre_archivo=nombre_archivo))
                
                if info.existe:
                    self.log(f"Metadatos recibidos: {info.tamano_bytes} bytes ({info.total_chunks} chunks).")
                    return info.total_chunks
                else:
                    self.log(f"El peer {address} dice que no tiene el archivo.")
                    return 0
        except Exception as e:
            self.log(f"Error obteniendo info de {peer_address}: {e}")
            return 0

    def _descargar_un_chunk(self, peer, nombre_archivo, indice):
        try:
            with grpc.insecure_channel(peer) as channel:
                stub = bittorrent_pb2_grpc.P2PServiceStub(channel)
                req = bittorrent_pb2.PeticionChunk(nombre_archivo=nombre_archivo, indice_chunk=indice)
                resp = stub.SolicitarChunk(req)
                
                if resp.encontrado and resp.datos:
                    ruta_destino = os.path.join(self.mi_carpeta, nombre_archivo)
                    with open(ruta_destino, 'r+b') as f:
                        f.seek(indice * CHUNK_SIZE)
                        f.write(resp.datos)
                    self.log(f"Chunk #{indice} descargado de {peer}")
                    return True
                else:
                    return False
        except Exception as e:
            self.log(f"Error descargando chunk {indice}: {e}")
            return False

if __name__ == "__main__":
    app = NodoGUI()
    app.mainloop()
