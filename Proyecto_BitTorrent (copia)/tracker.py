import grpc
from concurrent import futures
import time

# Importamos los módulos generados
import bittorrent_pb2
import bittorrent_pb2_grpc

class TrackerServicer(bittorrent_pb2_grpc.TrackerServiceServicer):
    def __init__(self):
        # Estructura de datos en memoria:
        # Clave: Nombre del archivo
        # Valor: Lista de IPs que lo tienen (ej. ['localhost:5001', '192.168.1.5:5002'])
        self.catalogo_archivos = {}
        
        # Para mostrar en consola (PDF Requisito 2): Guardamos info extra de los nodos
        self.nodos_activos = {} # { "ip:puerto": ["archivo1", "archivo2"] }

    def RegistrarNodo(self, request, context):
        """
        Cuando un nodo se conecta, nos manda su IP y lista de archivos.
        """
        ip_nodo = request.ip_puerto
        archivos = request.archivos
        
        # 1. Guardar o actualizar al nodo en la lista de activos
        self.nodos_activos[ip_nodo] = archivos
        
        # 2. Indexar sus archivos en el catálogo global
        for archivo in archivos:
            if archivo not in self.catalogo_archivos:
                self.catalogo_archivos[archivo] = []
            
            # Evitar duplicados si el nodo se registra dos veces
            if ip_nodo not in self.catalogo_archivos[archivo]:
                self.catalogo_archivos[archivo].append(ip_nodo)
        
        print(f"\n[TRACKER] Nodo conectado: {ip_nodo}")
        print(f"          Archivos compartidos: {archivos}")
        self._imprimir_estado_red() # Cumple con mostrar estado en consola
        
        return bittorrent_pb2.AckTracker(exito=True, mensaje="Registrado correctamente")

    def BuscarArchivo(self, request, context):
        """
        Un nodo pregunta quién tiene un archivo específico.
        """
        nombre = request.nombre_archivo
        peers = self.catalogo_archivos.get(nombre, [])
        
        print(f"\n[TRACKER] Búsqueda recibida: Alguien busca '{nombre}'")
        print(f"          Peers encontrados: {peers}")
        
        return bittorrent_pb2.ListaPeers(peers_con_archivo=peers)

    def _imprimir_estado_red(self):
        """
        Función auxiliar para cumplir el requisito de mostrar el estado de la red.
        """
        print("-" * 40)
        print(" ESTADO ACTUAL DE LA RED BITTORRENT")
        print("-" * 40)
        print(f"Total Nodos: {len(self.nodos_activos)}")
        for ip, archivos in self.nodos_activos.items():
            print(f" -> Nodo {ip}: Comparte {len(archivos)} archivos")
        print("-" * 40)

def serve():
    # Iniciamos el servidor gRPC
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    bittorrent_pb2_grpc.add_TrackerServiceServicer_to_server(TrackerServicer(), server)
    
    # El Tracker escuchará en el puerto 50051 (puedes cambiarlo si quieres)
    puerto = "50051"
    server.add_insecure_port(f'[::]:{puerto}')
    print(f"[*] Tracker iniciado en el puerto {puerto}")
    print("[*] Esperando nodos...")
    
    server.start()
    try:
        # Mantenemos el hilo principal vivo
        while True:
            time.sleep(86400)
    except KeyboardInterrupt:
        server.stop(0)

if __name__ == '__main__':
    serve()
