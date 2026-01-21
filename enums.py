from enum import Enum


class BodyPart(Enum):
    HEAD = "cabeca"
    TORSO = "torso"
    ARMS = "bracos"
    LEGS = "pernas"


class MonsterType(Enum):
    NECROPHAGE = "Necrophage"
    SPECTER = "Specter"


class SheetSection(Enum):
    GENERAL = "geral"
    COMBAT = "combate"
    ATTRIBUTES = "atributos"
    MAGIC = "magia"
    INVENTORY = "inventario"
