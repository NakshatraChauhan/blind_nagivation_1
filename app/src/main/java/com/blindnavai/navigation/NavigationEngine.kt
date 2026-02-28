package com.blindnavai.navigation

import android.content.Context
import com.blindnavai.voice.VoiceManager
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import org.json.JSONObject
import org.osmdroid.util.GeoPoint
import org.osmdroid.views.MapView
import org.osmdroid.views.overlay.Polyline
import java.io.BufferedReader
import java.io.InputStreamReader
import kotlin.math.atan2

class NavigationEngine(
    private val context: Context,
    private val mapView: MapView,
    private val voiceManager: VoiceManager
) {
    private val router = AStarRouter()
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Default)

    private var graph: AStarRouter.Graph? = null
    private var currentLocation: GeoPoint? = null
    private var routePoints: List<AStarRouter.Node> = emptyList()
    private var routeIndex = 0
    private var navJob: Job? = null
    private var isPausedByHazard = false

    init {
        graph = loadGraphFromAssets("osm_graph.json")
    }

    fun updateCurrentLocation(point: GeoPoint) {
        currentLocation = point
    }

    fun pauseForHazard() {
        isPausedByHazard = true
    }

    fun resumeAfterHazard() {
        isPausedByHazard = false
    }

    fun startNavigation(destination: GeoPoint, onStatus: (String) -> Unit) {
        val g = graph ?: run {
            onStatus("No offline graph found. Add assets/osm_graph.json")
            return
        }
        val start = currentLocation ?: GeoPoint(g.nodes.values.first().lat, g.nodes.values.first().lon)
        val startId = nearestNodeId(start, g)
        val destinationId = nearestNodeId(destination, g)
        routePoints = router.route(g, startId, destinationId)
        routeIndex = 1
        drawRoute(routePoints)

        navJob?.cancel()
        navJob = scope.launch {
            while (routeIndex < routePoints.size) {
                if (isPausedByHazard) {
                    delay(500)
                    continue
                }
                val current = currentLocation ?: break
                val target = routePoints[routeIndex]
                val distance = current.distanceToAsDouble(GeoPoint(target.lat, target.lon))
                if (distance < 8.0) {
                    routeIndex++
                    continue
                }

                if (routeIndex + 1 < routePoints.size) {
                    val next = routePoints[routeIndex + 1]
                    val instruction = computeTurnInstruction(target, next)
                    onStatus("$instruction in ${distance.toInt()} m")
                    voiceManager.enqueueNavigation("$instruction in ${distance.toInt()} meters")
                } else {
                    onStatus("Destination ahead in ${distance.toInt()} m")
                    voiceManager.enqueueNavigation("Destination ahead in ${distance.toInt()} meters")
                }
                delay(6_000)
            }
            if (routePoints.isNotEmpty()) {
                onStatus("Arrived at destination")
                voiceManager.enqueueNavigation("You have arrived at your destination")
            }
        }
    }

    private fun drawRoute(nodes: List<AStarRouter.Node>) {
        if (nodes.isEmpty()) return
        val line = Polyline().apply {
            setPoints(nodes.map { GeoPoint(it.lat, it.lon) })
            color = android.graphics.Color.BLUE
            width = 8f
        }
        mapView.overlays.removeAll { it is Polyline }
        mapView.overlays.add(line)
        mapView.invalidate()
    }

    private fun nearestNodeId(point: GeoPoint, graph: AStarRouter.Graph): String {
        return graph.nodes.values.minByOrNull {
            point.distanceToAsDouble(GeoPoint(it.lat, it.lon))
        }?.id ?: graph.nodes.keys.first()
    }

    private fun computeTurnInstruction(current: AStarRouter.Node, next: AStarRouter.Node): String {
        val bearing = atan2(next.lon - current.lon, next.lat - current.lat)
        val degree = Math.toDegrees(bearing)
        return when {
            degree > 30 -> "Turn right"
            degree < -30 -> "Turn left"
            else -> "Continue straight"
        }
    }

    private fun loadGraphFromAssets(fileName: String): AStarRouter.Graph? {
        return try {
            val raw = context.assets.open(fileName).use { input ->
                BufferedReader(InputStreamReader(input)).readText()
            }
            val json = JSONObject(raw)
            val nodeArr = json.getJSONArray("nodes")
            val edgeArr = json.getJSONArray("edges")

            val nodes = mutableMapOf<String, AStarRouter.Node>()
            for (i in 0 until nodeArr.length()) {
                val n = nodeArr.getJSONObject(i)
                val id = n.getString("id")
                nodes[id] = AStarRouter.Node(id, n.getDouble("lat"), n.getDouble("lon"))
            }

            val edges = mutableMapOf<String, MutableList<AStarRouter.Edge>>()
            for (i in 0 until edgeArr.length()) {
                val e = edgeArr.getJSONObject(i)
                val edge = AStarRouter.Edge(
                    from = e.getString("from"),
                    to = e.getString("to"),
                    weightMeters = e.getDouble("weight")
                )
                edges.getOrPut(edge.from) { mutableListOf() }.add(edge)
            }

            AStarRouter.Graph(nodes = nodes, edges = edges)
        } catch (_: Exception) {
            null
        }
    }
}
