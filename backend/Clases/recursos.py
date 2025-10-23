class Recursos:
    def __init__(self, id, nombre, abreviatura, metrica, tipo, valorxhora):
        self.id = id
        self.nombre = nombre
        self.abreviatura = abreviatura
        self.metrica = metrica
        self.tipo = tipo
        self.valorxhora = valorxhora

    def getId(self):
        return self.id

    def getInfo(self):
        return {
            "id": self.id,
            "nombre": self.nombre,
            "abreviatura": self.abreviatura,
            "metrica": self.metrica,
            "tipo": self.tipo,
            "valorxhora": self.valorxhora,
        }
