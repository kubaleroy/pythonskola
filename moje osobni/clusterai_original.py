import numpy as np
from numba import jit, cuda, njit, prange

"""
structure:
input layer of size X > connects to cluster of neurons all interconnected > output layer of size Y+1
recursion occurs in the cluster of neurons, where each neuron takes the output of all other neurons as input, dedicated output neuron as the "Decision" when decision > threshold is met, the output layer is activated and the network returns the output of the output layer
input weights: 
    each connects to each neuron in cluster.
cluster:
    each neuron connects to each other neuron in cluster, to the output layer, and to the dedicated output neuron.
output layer:
    all clusterNeurons connect to each output neuron.

"""
OUTPUT_NEURON_THRESHOLD = 0.9
OUTPUT_NEURON_SIZE = 5
INPUT_NEURON_SIZE = 5


def buildCluster(size):
    """
    build n neurons all interconnected to each other, with random weights and biases
    """
    weights = np.random.rand(size, size)
    biases = np.random.rand(size+OUTPUT_NEURON_SIZE+INPUT_NEURON_SIZE+1)
    return weights, biases

def sigmoid(x):
    return 1 / (1 + np.exp(-x))

def iteration(weights, biases, input):
    """
    forward pass through the cluster
    """
    output = np.zeros(len(biases)-INPUT_NEURON_SIZE-OUTPUT_NEURON_SIZE)
    for i in range(len(biases)-INPUT_NEURON_SIZE-OUTPUT_NEURON_SIZE):
        i = i + INPUT_NEURON_SIZE
        output[i] = sigmoid(np.dot(weights[i], input) + biases[i])
    return output

def runCluster(weights, biases, input):
    """
    run the cluster until the output neuron is activated
    """
    output = iteration(weights, biases, input)
    while True:
        output = iteration(weights, biases, output)
        if output[-1] > OUTPUT_NEURON_THRESHOLD:
            break
    return output

def runNetwork(weights, biases, input):
    """
    run the network until the output neuron is activated
    """
    output = runCluster(weights, biases, input)
    outLayer = []
    for i in range(OUTPUT_NEURON_SIZE):
        i = i + 1 
        outLayer.append(np.dot(weights[-i], output))
    return outLayer

def main():
    weights, biases = buildCluster(10)
    input = np.random.rand(INPUT_NEURON_SIZE)
    output = runNetwork(weights, biases, input)
    print(output)
    
if __name__ == "__main__":
    main()