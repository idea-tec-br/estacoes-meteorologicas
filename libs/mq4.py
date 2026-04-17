from libs.basemq import BaseMQ


class MQ4(BaseMQ):
    def __init__(self, pinData, pinHeater=-1):
        super().__init__(pinData, pinHeater)

    def getRoInCleanAir(self):
        # Valor típico do datasheet: Rs/Ro ≈ 4.4 em ar limpo
        return 4.4

    def readMethane(self):
        # Coeficientes da curva log(ppm) = a * log(Rs/Ro) + b
        return self.readScaled(-0.36, 2.54)
