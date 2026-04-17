import ujson as json
import os
from math import radians, cos, sin, sqrt, atan2


class GPSFixManager:
    def __init__(self, arquivo_fix="fix.json", limite_metros=500, tentativas=3):
        self.arquivo_fix = arquivo_fix
        self.limite_metros = limite_metros
        self.tentativas = tentativas

    def distancia_metros(self, lat1, lon1, lat2, lon2):
        R = 6371000  # raio da Terra em metros
        dlat = radians(lat2 - lat1)
        dlon = radians(lon2 - lon1)
        a = (
            sin(dlat / 2) ** 2
            + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
        )
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        return R * c

    def salvar_fix(self, dados):
        try:
            with open(self.arquivo_fix, "w") as f:
                json.dump(dados, f)
        except Exception as e:
            print("Erro ao salvar fix:", e)

    def carregar_fix(self):
        try:
            if self.arquivo_fix in os.listdir():
                with open(self.arquivo_fix, "r") as f:
                    return json.load(f)
        except Exception as e:
            print("Erro ao carregar fix:", e)
        return None

    def fix_valido(self, fix):
        if fix is None:
            return False
        try:
            lat = float(fix.get("latitude"))
            lon = float(fix.get("longitude"))
            if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                return False
            # Pode adicionar mais validações se quiser (ex: altitude numérica)
            return True
        except:
            return False

    def pegar_fix_consistente(self, gps_data_func):
        fixes = []
        tentativas_restantes = (
            self.tentativas * 3
        )  # ou mais para garantir pegar 3 fixes válidos

        while len(fixes) < 3 and tentativas_restantes > 0:
            fix = gps_data_func()
            if self.fix_valido(fix):
                fixes.append(fix)
            tentativas_restantes -= 1

        if len(fixes) < 3:
            # Se não conseguiu 3 fixes válidos, devolve o melhor que tem ou None
            if fixes:
                return fixes[0]
            return None

        # Agora temos 3 fixes válidos, vamos escolher o mais consistente

        # Função pra calcular distância entre dois fixes
        def dist(f1, f2):
            return self.distancia_metros(
                float(f1["latitude"]),
                float(f1["longitude"]),
                float(f2["latitude"]),
                float(f2["longitude"]),
            )

        # Calcula distâncias entre cada par
        d01 = dist(fixes[0], fixes[1])
        d12 = dist(fixes[1], fixes[2])
        d02 = dist(fixes[0], fixes[2])

        # Se um fix estiver longe dos outros dois, descartamos ele e escolhemos o mais próximo entre os outros dois
        # Caso contrário, escolhemos o fix do meio (mediana) — nesse caso o que tem a menor soma das distâncias
        if d01 > self.limite_metros and d02 > self.limite_metros:
            # fix 0 está longe dos outros dois, escolhe entre fix 1 e 2
            soma_12 = d12
            return fixes[1] if soma_12 < d12 else fixes[2]
        if d01 > self.limite_metros and d12 > self.limite_metros:
            # fix 1 está longe, escolhe entre fix 0 e 2
            soma_02 = d02
            return fixes[0] if soma_02 < d02 else fixes[2]
        if d12 > self.limite_metros and d02 > self.limite_metros:
            # fix 2 está longe, escolhe entre fix 0 e 1
            soma_01 = d01
            return fixes[0] if soma_01 < d01 else fixes[1]

        # Se todos próximos, escolhe o fix que tem a menor soma das distâncias para os outros dois (mais "central")
        soma_distancias = []
        for i in range(3):
            soma = 0
            for j in range(3):
                if i != j:
                    soma += dist(fixes[i], fixes[j])
            soma_distancias.append((soma, fixes[i]))

        soma_distancias.sort(key=lambda x: x[0])
        return soma_distancias[0][1]

    def atualizar_fix(self, gps_data):
        if not self.fix_valido(gps_data):
            print("Fix inválido, não será atualizado")
            return False

        fix_antigo = self.carregar_fix()
        if fix_antigo is None:
            self.salvar_fix(gps_data)
            print("Primeiro fix salvo:", gps_data)
            return True

        distancia = self.distancia_metros(
            float(fix_antigo["latitude"]),
            float(fix_antigo["longitude"]),
            float(gps_data["latitude"]),
            float(gps_data["longitude"]),
        )

        if distancia > self.limite_metros:
            self.salvar_fix(gps_data)
            print(f"Fix atualizado. Distância entre fixes: {distancia:.2f} m")
            return True
        else:
            print(
                f"Mudança menor que {self.limite_metros} metros ({distancia:.2f} m). Fix mantido."
            )
            return False
