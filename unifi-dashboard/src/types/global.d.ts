// Global type declarations for the MYCA UniFi Dashboard

declare global {
  // SpeechRecognition API types
  interface SpeechRecognitionEvent extends Event {
    readonly resultIndex: number
    readonly results: SpeechRecognitionResultList
  }

  interface SpeechRecognitionResultList {
    readonly length: number
    item(index: number): SpeechRecognitionResult
    [index: number]: SpeechRecognitionResult
  }

  interface SpeechRecognitionResult {
    readonly length: number
    readonly isFinal: boolean
    item(index: number): SpeechRecognitionAlternative
    [index: number]: SpeechRecognitionAlternative
  }

  interface SpeechRecognitionAlternative {
    readonly transcript: string
    readonly confidence: number
  }

  interface SpeechRecognitionErrorEvent extends Event {
    readonly error: string
    readonly message: string
  }

  interface SpeechRecognition extends EventTarget {
    continuous: boolean
    interimResults: boolean
    lang: string
    maxAlternatives: number
    onaudioend: ((this: SpeechRecognition, ev: Event) => any) | null
    onaudiostart: ((this: SpeechRecognition, ev: Event) => any) | null
    onend: ((this: SpeechRecognition, ev: Event) => any) | null
    onerror: ((this: SpeechRecognition, ev: SpeechRecognitionErrorEvent) => any) | null
    onnomatch: ((this: SpeechRecognition, ev: Event) => any) | null
    onresult: ((this: SpeechRecognition, ev: SpeechRecognitionEvent) => any) | null
    onsoundend: ((this: SpeechRecognition, ev: Event) => any) | null
    onsoundstart: ((this: SpeechRecognition, ev: Event) => any) | null
    onspeechend: ((this: SpeechRecognition, ev: Event) => any) | null
    onspeechstart: ((this: SpeechRecognition, ev: Event) => any) | null
    onstart: ((this: SpeechRecognition, ev: Event) => any) | null
    abort(): void
    start(): void
    stop(): void
  }

  interface SpeechRecognitionStatic {
    new (): SpeechRecognition
    prototype: SpeechRecognition
  }

  // eslint-disable-next-line no-var
  var SpeechRecognition: SpeechRecognitionStatic
  // eslint-disable-next-line no-var
  var webkitSpeechRecognition: SpeechRecognitionStatic

  interface Window {
    SpeechRecognition: SpeechRecognitionStatic
    webkitSpeechRecognition: SpeechRecognitionStatic
  }

  // Three.js JSX element types (coarse, but unblocks TS)
  namespace JSX {
    interface IntrinsicElements {
      group: any
      mesh: any
      instancedMesh: any
      points: any
      line: any
      lineSegments: any
      gridHelper: any

      bufferGeometry: any
      bufferAttribute: any
      pointsMaterial: any
      lineBasicMaterial: any
      meshStandardMaterial: any
      meshBasicMaterial: any
      shaderMaterial: any

      sphereGeometry: any
      boxGeometry: any
      planeGeometry: any
      circleGeometry: any
      cylinderGeometry: any
      coneGeometry: any
      torusGeometry: any
      torusKnotGeometry: any
      ringGeometry: any
      octahedronGeometry: any
      icosahedronGeometry: any
      dodecahedronGeometry: any
      tetrahedronGeometry: any

      ambientLight: any
      pointLight: any
      directionalLight: any
      spotLight: any
      hemisphereLight: any

      primitive: any
    }
  }
}

export {}

