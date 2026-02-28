package com.blindnavai.navigation

import kotlin.math.abs

class AStarRouter {
    data class Node(val id: String, val lat: Double, val lon: Double)
    data class Edge(val from: String, val to: String, val weightMeters: Double)
    data class Graph(val nodes: Map<String, Node>, val edges: Map<String, List<Edge>>)

    fun route(graph: Graph, startId: String, goalId: String): List<Node> {
        if (startId == goalId) return listOfNotNull(graph.nodes[startId])

        val openSet = mutableSetOf(startId)
        val cameFrom = mutableMapOf<String, String>()
        val gScore = mutableMapOf(startId to 0.0)
        val fScore = mutableMapOf(startId to heuristic(graph, startId, goalId))

        while (openSet.isNotEmpty()) {
            val current = openSet.minByOrNull { fScore[it] ?: Double.MAX_VALUE } ?: break
            if (current == goalId) return reconstructPath(graph, cameFrom, current)

            openSet.remove(current)
            graph.edges[current].orEmpty().forEach { edge ->
                val tentativeG = (gScore[current] ?: Double.MAX_VALUE) + edge.weightMeters
                if (tentativeG < (gScore[edge.to] ?: Double.MAX_VALUE)) {
                    cameFrom[edge.to] = current
                    gScore[edge.to] = tentativeG
                    fScore[edge.to] = tentativeG + heuristic(graph, edge.to, goalId)
                    openSet.add(edge.to)
                }
            }
        }
        return emptyList()
    }

    private fun reconstructPath(graph: Graph, cameFrom: Map<String, String>, current: String): List<Node> {
        val path = mutableListOf(current)
        var cursor: String? = current
        while (cursor != null && cameFrom.containsKey(cursor)) {
            cursor = cameFrom[cursor]
            if (cursor != null) path.add(cursor)
        }
        path.reverse()
        return path.mapNotNull { graph.nodes[it] }
    }

    private fun heuristic(graph: Graph, fromId: String, toId: String): Double {
        val from = graph.nodes[fromId] ?: return Double.MAX_VALUE
        val to = graph.nodes[toId] ?: return Double.MAX_VALUE
        val dx = abs(from.lat - to.lat)
        val dy = abs(from.lon - to.lon)
        return (dx + dy) * 111_000.0
    }
}
