"""
Base de conocimientos para productos de energía solar.
"""
import logging
import pickle
import os

class ProductKnowledgeBase:
    """
    Base de conocimientos simple para productos de energía solar.
    """
    
    def __init__(self):
        """Inicializa la base de conocimientos."""
        self.documents = []
        self.index = {}
        
    def build_index(self, documents):
        """
        Construye el índice de la base de conocimientos.
        
        Args:
            documents (list): Lista de documentos sobre productos
        """
        try:
            self.documents = documents if documents else []
            
            # Crear un índice simple por palabras clave
            self.index = {}
            for i, doc in enumerate(self.documents):
                if isinstance(doc, dict) and 'content' in doc:
                    words = doc['content'].lower().split()
                    for word in words:
                        if word not in self.index:
                            self.index[word] = []
                        self.index[word].append(i)
            
            logging.info(f"Índice construido con {len(self.documents)} documentos")
            
        except Exception as e:
            logging.error(f"Error al construir índice: {str(e)}")
            self.documents = []
            self.index = {}
    
    def search(self, query, max_results=5):
        """
        Busca documentos relevantes para una consulta.
        
        Args:
            query (str): Consulta de búsqueda
            max_results (int): Máximo número de resultados
            
        Returns:
            list: Lista de documentos relevantes
        """
        try:
            if not query or not self.index:
                return []
            
            # Buscar documentos que contengan palabras de la consulta
            query_words = query.lower().split()
            doc_scores = {}
            
            for word in query_words:
                if word in self.index:
                    for doc_idx in self.index[word]:
                        if doc_idx not in doc_scores:
                            doc_scores[doc_idx] = 0
                        doc_scores[doc_idx] += 1
            
            # Ordenar por relevancia y retornar top resultados
            sorted_docs = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)
            results = []
            
            for doc_idx, score in sorted_docs[:max_results]:
                if doc_idx < len(self.documents):
                    results.append(self.documents[doc_idx])
            
            return results
            
        except Exception as e:
            logging.error(f"Error en búsqueda: {str(e)}")
            return []
    
    def save(self, filepath):
        """
        Guarda la base de conocimientos en un archivo.
        
        Args:
            filepath (str): Ruta del archivo
        """
        try:
            # Crear directorio si no existe
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            data = {
                'documents': self.documents,
                'index': self.index
            }
            
            with open(filepath, 'wb') as f:
                pickle.dump(data, f)
                
            logging.info(f"Base de conocimientos guardada en {filepath}")
            
        except Exception as e:
            logging.error(f"Error al guardar base de conocimientos: {str(e)}")
    
    def load(self, filepath):
        """
        Carga la base de conocimientos desde un archivo.
        
        Args:
            filepath (str): Ruta del archivo
        """
        try:
            with open(filepath, 'rb') as f:
                data = pickle.load(f)
            
            self.documents = data.get('documents', [])
            self.index = data.get('index', {})
            
            logging.info(f"Base de conocimientos cargada desde {filepath}")
            
        except FileNotFoundError:
            logging.warning(f"Archivo de base de conocimientos no encontrado: {filepath}")
            self.documents = []
            self.index = {}
        except Exception as e:
            logging.error(f"Error al cargar base de conocimientos: {str(e)}")
            self.documents = []
            self.index = {}