import { Canvas } from '@react-three/fiber'
import { OrbitControls, Environment, ContactShadows, Edges } from '@react-three/drei'

function hslForType(type, failed) {
  // Subtle but distinct palette, inspired by ThatOpen/davras5
  if (type === 'IfcWall') return failed ? '#f97316' : '#94a3b8'
  if (type === 'IfcDoor') return failed ? '#ef4444' : '#22c55e'
  if (type === 'IfcBeam') return '#8b5cf6'
  if (type === 'IfcPipeSegment' || type === 'IfcFlowSegment' || type === 'IfcDuctSegment') return '#0ea5e9'
  if (type === 'IfcSlab') return '#f59e0b'
  if (type === 'IfcColumn') return '#ec4899'
  return '#cbd5e1'
}

function Box({ pos, color, selected, type, onClick }) {
  const scale = type === 'IfcDoor' ? [0.9, 2.1, 0.05] : type === 'IfcBeam' ? [5, 0.35, 0.4] : type === 'IfcPipeSegment' ? [4, 0.18, 0.18] : [1, 0.6, 1]
  const args = type === 'IfcWall' ? [5, 3, 0.2] : scale
  return (
    <mesh position={pos} castShadow receiveShadow onClick={(e)=>{ e.stopPropagation(); onClick && onClick()}}>
      <boxGeometry args={args} />
      <meshStandardMaterial
        color={selected ? '#ef4444' : color}
        emissive={selected ? '#fecaca' : '#000000'}
        emissiveIntensity={selected ? 0.35 : 0}
        roughness={selected ? 0.5 : 0.75}
        metalness={0.08}
      />
      {selected && <Edges scale={1.02} threshold={15} color="#ef4444" />}
    </mesh>
  )
}

// Schematic locator — PBR + soft shadows + outline, honest about not being full IFC shape.
// True IFC via web-ifc-three would replace Box with IFCLoader mesh in production.
export default function Viewer({ elements, selectedGuid, failedDoorGuids = new Set(), onSelect }) {
  const items = elements.slice(0, 48).map((el, i) => {
    const p = el.placement || { x: (i % 6) * 2.5, y: Math.floor(i/6)*2.5, z: 0 }
    const isFailed = el.type === 'IfcDoor' && failedDoorGuids.has(el.guid)
    const color = hslForType(el.type, isFailed)
    const isSelected = selectedGuid && el.guid === selectedGuid
    const pos = [p.x, p.z + 0.5, -p.y]
    return { el, pos, color, isSelected }
  })

  if (!elements.length) {
    return (
      <div className="w-full h-full flex items-center justify-center bg-gray-50 text-sm text-gray-500 p-6 text-center">
        <div>
          <div className="font-medium">No model loaded</div>
          <div className="text-xs mt-1">Upload .ifc to visualize — schematic locator shows placements; true IFC geometry via web-ifc in production</div>
        </div>
      </div>
    )
  }

  return (
    <Canvas camera={{ position: [12, 10, 12], fov: 42 }} shadows dpr={[1, 1.8]}>
      <ambientLight intensity={0.55} />
      <directionalLight position={[10, 16, 8]} intensity={1.15} castShadow shadow-mapSize={[2048,2048]} shadow-bias={-0.0005} />
      <pointLight position={[-10, 10, -10]} intensity={0.35} />
      <hemisphereLight args={['#ffffff', '#e2e8f0', 0.35]} />
      <gridHelper args={[28, 28, '#e5e7eb', '#f1f5f9']} />
      <mesh rotation={[-Math.PI/2,0,0]} position={[0,-0.02,0]} receiveShadow>
        <planeGeometry args={[48,48]} />
        <meshStandardMaterial color="#f8fafc" roughness={0.92} metalness={0.02} />
      </mesh>
      {items.map(({ el, pos, color, isSelected }) => (
        <Box key={el.guid || el.name} pos={pos} color={color} selected={isSelected} type={el.type} onClick={()=>onSelect && onSelect(el.guid)} />
      ))}
      <ContactShadows position={[0,-0.48,0]} opacity={0.42} scale={28} blur={1.8} far={8} />
      <Environment preset="apartment" background={false} />
      <OrbitControls enableDamping dampingFactor={0.08} minDistance={4} maxDistance={40} />
    </Canvas>
  )
}
