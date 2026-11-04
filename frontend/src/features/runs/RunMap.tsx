import 'leaflet/dist/leaflet.css'
import { MapContainer, Polyline, TileLayer } from 'react-leaflet'
import type { ActivityStreams } from '../../api/types'

/** Route on OpenStreetMap tiles; renders nothing for activities without GPS. */
export default function RunMap(props: { streams: ActivityStreams }) {
  const { lat, lon } = props.streams
  if (!lat || !lon) return null
  const points = lat
    .map((la, i) => [la, lon[i]] as const)
    .filter((p): p is readonly [number, number] => p[0] !== null && p[1] !== null)
    .map(([la, lo]) => [la, lo] as [number, number])
  if (points.length < 2) return null
  return (
    <div className="card map-card">
      <MapContainer bounds={points} style={{ height: 260, borderRadius: 10 }} scrollWheelZoom={false}>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <Polyline positions={points} pathOptions={{ color: '#ff7a1a', weight: 4 }} />
      </MapContainer>
    </div>
  )
}
