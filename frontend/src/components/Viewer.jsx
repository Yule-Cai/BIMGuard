import { useEffect, useState, useMemo, useRef } from 'react'
import { Canvas, useThree } from '@react-three/fiber'
import { OrbitControls, Environment, ContactShadows, Edges } from '@react-three/drei'
import * as THREE from 'three'

// BIM palette — professional, not debug neon
function colorForElement(el, isFailed, isClash, isSelected) {
  if (isSelected) return '#ef4444'
  if (isFailed) return '#f87171' // subtle red tint for failed door
  if (isClash) return '#fb923c' // orange for clash pair
  // Normal palette
  switch (el.type) {
    case 'IfcWall': return '#d9dde3' // warm light grey
    case 'IfcSlab': return '#cfd4da' // light grey floor
    case 'IfcDoor': return '#a8b0b8' // muted grey/wood
    case 'IfcBeam': return '#737b86' // steel
    case 'IfcColumn': return '#7d8590'
    case 'IfcPipeSegment':
    case 'IfcFlowSegment':
    case 'IfcDuctSegment': return '#6b9dc7' // muted blue
    case 'IfcWindow': return '#a8c5e0'
    default: return '#cbd5e1'
  }
}

function RealMesh({ element, isSelected, isFailed, isClash, onClick }) {
  const meshRef = useRef()
  const geometry = useMemo(() => {
    const geom = new THREE.BufferGeometry()
    const verts = element.vertices
    const indices = element.indices
    if (!verts || !indices || verts.length === 0 || indices.length === 0) return null
    geom.setAttribute('position', new THREE.Float32BufferAttribute(verts, 3))
    geom.setIndex(indices)
    geom.computeVertexNormals()
    geom.computeBoundingBox()
    geom.computeBoundingSphere()
    return geom
  }, [element.vertices, element.indices])

  useEffect(() => {
    return () => { if (geometry) geometry.dispose() }
  }, [geometry])

  if (!geometry) return null

  const color = colorForElement(element, isFailed, isClash, isSelected)

  return (
    <mesh ref={meshRef} geometry={geometry} castShadow receiveShadow onClick={(e)=>{ e.stopPropagation(); onClick && onClick(element.guid)}}>
      <meshStandardMaterial
        color={color}
        emissive={isSelected ? '#fecaca' : isFailed ? '#fecaca' : isClash ? '#fed7aa' : '#000000'}
        emissiveIntensity={isSelected ? 0.35 : isFailed || isClash ? 0.18 : 0}
        roughness={0.78}
        metalness={0.06}
        transparent={false}
        side={THREE.DoubleSide}
      />
      {isSelected && <Edges scale={1.0} threshold={15} color="#ef4444" />}
      {isFailed && !isSelected && <Edges scale={1.0} threshold={15} color="#f87171" />}
      {isClash && !isSelected && <Edges scale={1.0} threshold={15} color="#fb923c" />}
    </mesh>
  )
}

function SchematicBox({ pos, color, selected, type, onClick }) {
  const args = type === 'IfcWall' ? [5, 3, 0.2] : type === 'IfcDoor' ? [0.9, 2.1, 0.05] : type === 'IfcBeam' ? [5, 0.35, 0.4] : type === 'IfcPipeSegment' ? [4, 0.18, 0.18] : [1, 0.6, 1]
  return (
    <mesh position={pos} castShadow receiveShadow onClick={(e)=>{ e.stopPropagation(); onClick && onClick()}}>
      <boxGeometry args={args} />
      <meshStandardMaterial color={selected ? '#ef4444' : color} emissive={selected ? '#fecaca' : '#000000'} emissiveIntensity={selected ? 0.35 : 0} roughness={0.75} metalness={0.08} />
      {selected && <Edges scale={1.02} threshold={15} color="#ef4444" />}
    </mesh>
  )
}

function CameraFit({ elements, geometryElements, onFit }) {
  const { camera, controls } = useThree()
  const hasRun = useRef(false)
  useEffect(() => {
    if (hasRun.current) return
    // Compute bounds from geometry or schematic
    let box = new THREE.Box3()
    let hasBox = false
    if (geometryElements && geometryElements.length) {
      geometryElements.forEach(el => {
        if (!el.vertices || el.vertices.length < 3) return
        for (let i=0;i<el.vertices.length;i+=3) {
          box.expandByPoint(new THREE.Vector3(el.vertices[i], el.vertices[i+1], el.vertices[i+2]))
          hasBox = true
        }
      })
    } else if (elements && elements.length) {
      elements.forEach((el,i) => {
        const p = el.placement || {x:(i%6)*2.5, y:Math.floor(i/6)*2.5, z:0}
        box.expandByPoint(new THREE.Vector3(p.x, p.z, -p.y))
        hasBox = true
      })
    }
    if (!hasBox) return
    const center = box.getCenter(new THREE.Vector3())
    const size = box.getSize(new THREE.Vector3())
    const maxDim = Math.max(size.x, size.y, size.z)
    const dist = maxDim * 1.6 + 4
    // Use Z-up for BIM (Z vertical), but Three is Y-up; our IFC is already in Y-up via vertices, so fit in Y-up
    camera.position.set(center.x + dist*0.7, center.y + dist*0.6, center.z + dist*0.7)
    camera.lookAt(center)
    // For OrbitControls, set target
    if (controls) {
      controls.target.copy(center)
      controls.update()
    }
    hasRun.current = true
    if (onFit) onFit(center, size)
  }, [elements, geometryElements, camera, controls, onFit])
  return null
}

export default function Viewer({ elements, selectedGuid, failedDoorGuids = new Set(), clashGuids = new Set(), onSelect, focusId }) {
  const [geometry, setGeometry] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [isReal, setIsReal] = useState(false)

  // Fetch real geometry when elements change (i.e., new IFC uploaded)
  useEffect(() => {
    let cancelled = false
    async function fetchGeom() {
      setLoading(true); setError(null)
      try {
        const r = await fetch('/api/geometry')
        if (!r.ok) {
          // No geometry or fallback
          if (!cancelled) { setGeometry(null); setIsReal(false) }
          return
        }
        const j = await r.json()
        if (!cancelled) {
          if (j.elements && j.elements.length) {
            setGeometry(j)
            setIsReal(true)
          } else {
            setGeometry(null)
            setIsReal(false)
          }
        }
      } catch (e) {
        if (!cancelled) { setGeometry(null); setIsReal(false); setError(e.message) }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    // Only fetch if we have elements (i.e., model loaded)
    if (elements && elements.length) fetchGeom()
    else { setGeometry(null); setIsReal(false) }
    return ()=>{ cancelled = true }
  }, [elements])

  // For schematic fallback
  const schematicItems = useMemo(() => {
    return elements.slice(0, 48).map((el, i) => {
      const p = el.placement || { x: (i % 6) * 2.5, y: Math.floor(i/6)*2.5, z: 0 }
      const isFailed = el.type === 'IfcDoor' && failedDoorGuids.has(el.guid)
      const isClash = clashGuids.has(el.guid)
      const color = colorForElement(el, isFailed, isClash, false)
      const isSelected = selectedGuid && el.guid === selectedGuid
      const pos = [p.x, p.z + 0.5, -p.y]
      return { el, pos, color, isSelected, isFailed, isClash }
    })
  }, [elements, failedDoorGuids, clashGuids, selectedGuid])

  // Focus handling: when focusId changes (issue click), animate camera to element
  const controlsRef = useRef()
  const handleFocus = (guidOrPair) => {
    // This is handled via selectedGuid and CameraFit, but we can also do smooth focus
    // For now, just set selected and let user orbit; full focus animation can be added
    if (guidOrPair && typeof guidOrPair === 'string') {
      onSelect && onSelect(guidOrPair)
    }
  }

  if (!elements.length) {
    return (
      <div className="w-full h-full flex items-center justify-center bg-gray-50 text-sm text-gray-500 p-6 text-center">
        <div>
          <div className="font-medium">No model loaded</div>
          <div className="text-xs mt-1">Upload .ifc to visualize — 3D IFC Viewer renders triangulated geometry</div>
        </div>
      </div>
    )
  }

  const showReal = isReal && geometry && geometry.elements && geometry.elements.length

  return (
    <div className="w-full h-full relative">
      <Canvas camera={{ position: [14, 12, 14], fov: 42 }} shadows dpr={[1, 1.8]} onCreated={({ gl }) => { gl.shadowMap.enabled = true }}>
        <ambientLight intensity={0.55} />
        <directionalLight position={[12, 18, 10]} intensity={1.1} castShadow shadow-mapSize={[2048,2048]} shadow-bias={-0.0005} />
        <pointLight position={[-10, 10, -10]} intensity={0.3} />
        <hemisphereLight args={['#ffffff', '#e2e8f0', 0.35]} />
        <gridHelper args={[32, 32, '#e5e7eb', '#f1f5f9']} position={[0, -0.02, 0]} />
        <mesh rotation={[-Math.PI/2,0,0]} position={[0,-0.03,0]} receiveShadow>
          <planeGeometry args={[48,48]} />
          <meshStandardMaterial color="#f8fafc" roughness={0.92} metalness={0.02} />
        </mesh>

        {showReal ? (
          geometry.elements.map(el => {
            const isFailed = el.type === 'IfcDoor' && failedDoorGuids.has(el.guid)
            const isClash = clashGuids.has(el.guid)
            const isSelected = selectedGuid === el.guid
            return <RealMesh key={el.guid} element={el} isSelected={isSelected} isFailed={isFailed} isClash={isClash} onClick={onSelect} />
          })
        ) : (
          schematicItems.map(({ el, pos, color, isSelected, isFailed, isClash }) => (
            <SchematicBox key={el.guid || el.name} pos={pos} color={isFailed ? '#f87171' : isClash ? '#fb923c' : color} selected={isSelected} type={el.type} onClick={()=>onSelect && onSelect(el.guid)} />
          ))
        )}

        <ContactShadows position={[0,-0.48,0]} opacity={0.38} scale={30} blur={1.8} far={10} />
        <Environment preset="apartment" background={false} />
        <OrbitControls ref={controlsRef} enableDamping dampingFactor={0.08} minDistance={3} maxDistance={60} />
        <CameraFit elements={elements} geometryElements={showReal ? geometry.elements : null} />
      </Canvas>

      {/* Overlay badges */}
      <div className="absolute top-2 left-2 flex gap-2 text-xs">
        <span className={`px-2 py-1 rounded ${showReal ? 'bg-green-100 text-green-700' : 'bg-amber-100 text-amber-700'}`}>
          {showReal ? `IFC Model Viewer · ${geometry.stats.triangles} tris` : 'Geometry unavailable — schematic fallback'}
        </span>
        {loading && <span className="bg-gray-100 px-2 py-1 rounded">Loading geometry…</span>}
        {error && <span className="bg-red-100 text-red-700 px-2 py-1 rounded">{error}</span>}
      </div>
      <div className="absolute bottom-2 left-2 text-xs bg-white/80 backdrop-blur px-2 py-1 rounded border">
        <span className="text-gray-600">Legend:</span> <span style={{color: '#d9dde3'}}>■ Wall</span> <span style={{color: '#a8b0b8'}}>■ Door</span> <span style={{color: '#f87171'}}>■ Fail</span> <span style={{color: '#737b86'}}>■ Beam</span> <span style={{color: '#6b9dc7'}}>■ Pipe</span> <span style={{color: '#fb923c'}}>■ Clash</span>
      </div>
    </div>
  )
}
