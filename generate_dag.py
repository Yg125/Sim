# 自己参照read_dag编写的，返回DAG的相关信息包括节点数，处理器数，计算矩阵VxP（时间）和邻接矩阵VxV（数据量）
import pydot
import numpy as np
from random import gauss
from environment import B_aver, servers, cloud
from os import system
from heft_mine import HEFT
import os 
np.random.seed(1)


def generate_dag(filename, ccr=0.4):
    graph = pydot.graph_from_dot_file(filename)[0]
    n_nodes = len(graph.get_nodes())

    # get adjacency matrix for DAG
    adj_matrix = np.full((n_nodes, n_nodes), -1)
    n_edges = 0
    for e in graph.get_edge_list():
        adj_matrix[int(e.get_source())-1][int(e.get_destination())-1] = 0
        n_edges += 1

    # if DAG has multiple entry/exit nodes, create dummy nodes in its place
    ends = np.nonzero(np.all(adj_matrix==-1, axis=1))[0]    # exit nodes
    starts = np.nonzero(np.all(adj_matrix==-1, axis=0))[0]  # entry nodes
    start_node = pydot.Node("0", alpha="\"0\"", size="\"0\"")
    end_node = pydot.Node(str(n_nodes+1), alpha="\"0\"", size="\"0\"")
    graph.add_node(start_node)
    graph.add_node(end_node)

    for start in starts:
        s_edge = pydot.Edge("0", str(start+1), size="\"0\"")
        graph.add_edge(s_edge)
        
    for end in ends:
        e_edge = pydot.Edge(str(end+1), str(n_nodes+1), size="\"0\"")
        graph.add_edge(e_edge)

    n_nodes = len(graph.get_nodes())

    # construct computation matrix
    comp_matrix = np.empty((n_nodes, 6))
    comp_total = 0
    for n in graph.get_node_list():
        size_str = n.obj_dict['attributes']['alpha']
        size = float(size_str.split('\"')[1])
        if size==0:
            comp_matrix[int(n.get_name())][:] = 0
        else:
            # mi = np.random.randint(low=100, high=500)   # MI per task
            mi = abs(np.random.normal(0.01,0.025)) * 10**4     # MI per task
            comp_temp = []
            for i in range(5):
                comp_temp.append(round(mi / servers[i].comp * 1000, 1))   # calculate time  ms
            comp_temp.append(round(mi / cloud.comp * 1000, 1))
            comp_matrix[int(n.get_name())][:] = comp_temp
            comp_total += np.average(comp_temp)


    # get modified adjency matrix  
    # return Bytes of each edge
    adj_matrix = np.full((n_nodes, n_nodes), -1)
    mu = ccr*comp_total*10**6/(B_aver*n_edges)     # Byte per edge
    for e in graph.get_edge_list():
        source, dest = int(e.get_source()), int(e.get_destination())
        if dest == n_nodes -1:
            adj_matrix[source][dest] = 0                             # return time ignore
        elif source == 0:
            data_in = np.random.uniform(low=1, high=3)            # MB
            # adj_matrix[source][dest] = round(data_in * B_u * 2**20 / 10**6, 1)   # input time
            adj_matrix[source][dest] = data_in * 2**20               # Byte
        else:
            # adj_matrix[source][dest] = round(abs(gauss(mu, mu/4))*B_aver/10**6, 1)   # communication time  ms
            adj_matrix[source][dest] = abs(gauss(mu, mu/4))

    return [n_nodes, comp_matrix, adj_matrix]


if __name__ == "__main__":
    results = []
    for i in range(200):
        # result = generate_dag('dags/sim_0.dot')
        files = os.listdir('dags_dot')
        file = np.random.choice(files)
        result = generate_dag(os.path.join('dags_dot', file))
        makespan = HEFT(i, result).makespan
        result.append(makespan)
        results.append(result)
    np.save(f'dag_info.npy', results)
    
    
            
        
    # n_nodes, comp_matrix, adj_matrix = generate_dag('test2.dot')
    # print('No. of nodes: {}\nComputation Matrix:\n{}\nAdjacency Matrix:\n{}\n'.format(
    # n_nodes, comp_matrix, adj_matrix))
    
    # 每次生成的 DAG 都不一样，但是生成的 DAG 的结构是一样的，只是每个节点的计算时间和通信时间不一样，符合正态分布
    # 生成的 DAG 的结构如下：
    # daggen-master/daggen -n 20 --fat 0.5 --density 0.5 --regular 0.5 --jump 2 --minalpha 20 --maxalpha 50 --dot -o sim.dot
    # 定义边缘服务器，在这里直接改造comp和adj矩阵