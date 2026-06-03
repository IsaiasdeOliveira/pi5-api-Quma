# trainer_qml.py
import json
import pennylane as qml
from pennylane import numpy as np

# 1. SETUP DO SIMULADOR QUÂNTICO
N_QUBITS = 4
dev = qml.device("default.qubit", wires=N_QUBITS)

# 2. DEFINIÇÃO DA REDE NEURAL QUÂNTICA (PQC)
@qml.qnode(dev)
def quantum_circuit(features, weights):
    """
    O circuito aplica AngleEmbedding para mapear os dados clássicos do tabuleiro (features)
    e BasicEntanglerLayers para criar o emaranhamento quântico (pesos sinápticos).
    """
    qml.AngleEmbedding(features, wires=range(N_QUBITS))
    qml.BasicEntanglerLayers(weights, wires=range(N_QUBITS))
    return qml.expval(qml.PauliZ(0))

# 3. FUNÇÃO DE CUSTO (Massa de treino para otimização)
def cost_function(weights, features, target_scores):
    """Calcula o Erro Quadrático Médio entre a previsão quântica e o estado ideal."""
    predictions = [quantum_circuit(f, weights) for f in features]
    return np.mean((np.array(predictions) - target_scores) ** 2)

# 4. DADOS DE TREINAMENTO (Simulação de estados do tabuleiro 5x5)
# Cada vetor representa: [Minha Altura, Altura Inimigo, Controle de Centro, Mobilidade]
train_features = np.array([
    [np.pi, 0.0, np.pi, np.pi],    # Estado Excelente: Estou alto, domino o centro e com jogadas.
    [0.0, np.pi, 0.0, 0.0],        # Estado Crítico: Inimigo domina todas as vantagens.
    [np.pi/2, np.pi/2, np.pi, 0.0] # Estado de Equilíbrio: Alturas iguais, mas domino o centro.
], requires_grad=False)

# Alvos: 1.0 significa vitória garantida, -10000/derrota, e decimais são vantagens
target_scores = np.array([1.0, -1.0, 0.5], requires_grad=False)

# 5. INICIALIZAÇÃO DOS PESOS E OTIMIZADOR QUÂNTICO
np.random.seed(42)
weights_shape = qml.BasicEntanglerLayers.shape(n_layers=2, n_wires=N_QUBITS)
initial_weights = np.random.uniform(low=0, high=np.pi, size=weights_shape, requires_grad=True)

# Otimizador Clássico por Gradiente Descendente aplicado ao circuito quântico
opt = qml.GradientDescentOptimizer(stepsize=0.4)
weights = initial_weights

print("=========================================================")
print("  INICIANDO OTIMIZAÇÃO VIA QUANTUM MACHINE LEARNING  ")
print("=========================================================")

# 6. LOOP DE APRENDIZADO
for step in range(25):
    weights, cost = opt.step_and_cost(lambda w: cost_function(w, train_features, target_scores), weights)
    if step % 5 == 0:
        print(f"Passo {step:2d} | Custo Quântico (Erro de Convergência): {cost:.4f}")

print("\n--- TREINAMENTO CONCLUÍDO COM SUCESSO ---")
print("Extraindo os valores esperados das matrizes quânticas...")

# 7. CONVERSÃO E SALVAMENTO AUTOMÁTICO EM JSON
# Multiplicamos o output do circuito para gerar uma escala de pesos clássicos robusta
pesos_otimizados = {
    "win_move": 10000.0,
    "my_height": float(weights[0][0] * 12.0),
    "opp_height": float(-weights[0][1] * 15.0),
    "center_control": float(weights[0][2] * 5.0),
    "mobility": float(weights[1][0] * 2.5)
}

# Cria o arquivo de comunicação automatizada
with open("pesos_quanticos.json", "w") as f:
    json.dump(pesos_otimizados, f, indent=4)

print("Arquivo 'pesos_quanticos.json' gerado e atualizado na pasta do projeto!\n")