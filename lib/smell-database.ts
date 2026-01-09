/**
 * MINDEX Smell Encyclopedia - Fungal Smell Database
 * 
 * This module defines smell signatures for BME688/BSEC2 gas classification.
 * The gas_class values (0-3) correspond to BSEC_OUTPUT_GAS_ESTIMATE_1..4
 * 
 * Training data for BSEC2 should be collected using Bosch BME AI-Studio
 * and the resulting config blob stored in bsec_selectivity.h
 */

export interface SmellSignature {
  id: string
  name: string
  category: "fungal" | "plant" | "chemical" | "animal" | "fire" | "decay" | "clean"
  subcategory: string
  description: string
  
  // BSEC gas class mapping (0-3)
  bsec_class_id: number
  
  // VOC fingerprint for training
  voc_pattern: {
    ethanol?: number      // 0-1 relative concentration
    octanol?: number      // 1-octen-3-ol (mushroom alcohol)
    acetaldehyde?: number
    methanol?: number
    hydrogen_sulfide?: number
    ammonia?: number
    co2?: number
    other?: number
  }
  
  // Visual representation
  icon_type: "fungus" | "mushroom" | "mycelium" | "spore" | "decay" | "warning" | "plant" | "fire" | "chemical" | "clean"
  color_hex: string
  
  // For species-specific smells
  species_id?: string
  species_name?: string
  
  // Training data
  training_samples: number
  confidence_threshold: number
  
  // Metadata
  created_at: string
  updated_at: string
}

// Initial fungal smell database - focused on mycology
export const FUNGAL_SMELL_DATABASE: SmellSignature[] = [
  // Class 0: Fresh Mushroom / Fruiting Body
  {
    id: "smell-001",
    name: "Fresh Mushroom Fruiting",
    category: "fungal",
    subcategory: "basidiomycete",
    description: "The characteristic earthy, umami smell of fresh mushroom fruiting bodies. Dominated by 1-octen-3-ol (mushroom alcohol) with hints of ethanol.",
    bsec_class_id: 0,
    voc_pattern: {
      octanol: 0.45,
      ethanol: 0.25,
      acetaldehyde: 0.15,
      other: 0.15
    },
    icon_type: "mushroom",
    color_hex: "#8B4513",
    training_samples: 0,
    confidence_threshold: 0.75,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString()
  },
  
  // Class 1: Mycelium Growth
  {
    id: "smell-002",
    name: "Active Mycelium Growth",
    category: "fungal",
    subcategory: "mycelial",
    description: "Earthy, musty smell of actively growing mycelium colonizing substrate. Lower intensity than fruiting, more soil-like.",
    bsec_class_id: 1,
    voc_pattern: {
      ethanol: 0.30,
      octanol: 0.20,
      co2: 0.25,
      other: 0.25
    },
    icon_type: "mycelium",
    color_hex: "#F5F5DC",
    training_samples: 0,
    confidence_threshold: 0.70,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString()
  },
  
  // Class 2: Substrate Decomposition
  {
    id: "smell-003",
    name: "Substrate Decomposition",
    category: "decay",
    subcategory: "fermentation",
    description: "Fermentation and decomposition smell from substrate breakdown. Higher ammonia and hydrogen sulfide notes.",
    bsec_class_id: 2,
    voc_pattern: {
      ethanol: 0.20,
      ammonia: 0.25,
      hydrogen_sulfide: 0.15,
      co2: 0.20,
      other: 0.20
    },
    icon_type: "decay",
    color_hex: "#654321",
    training_samples: 0,
    confidence_threshold: 0.65,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString()
  },
  
  // Class 3: Contamination Warning
  {
    id: "smell-004",
    name: "Contamination Alert",
    category: "fungal",
    subcategory: "contamination",
    description: "Unusual VOC profile indicating possible contamination (Trichoderma, bacteria, mold). Sharp, chemical or sour notes.",
    bsec_class_id: 3,
    voc_pattern: {
      acetaldehyde: 0.30,
      ammonia: 0.20,
      hydrogen_sulfide: 0.20,
      other: 0.30
    },
    icon_type: "warning",
    color_hex: "#FF4500",
    training_samples: 0,
    confidence_threshold: 0.60,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString()
  },
  
  // Additional common mushroom species signatures
  {
    id: "smell-010",
    name: "Agaricus bisporus",
    category: "fungal",
    subcategory: "basidiomycete",
    description: "Common white/brown button mushroom. Mild, slightly sweet earthy smell.",
    bsec_class_id: 0,
    voc_pattern: {
      octanol: 0.50,
      ethanol: 0.20,
      acetaldehyde: 0.10,
      other: 0.20
    },
    icon_type: "mushroom",
    color_hex: "#F5DEB3",
    species_id: "species-agaricus-bisporus",
    species_name: "Agaricus bisporus",
    training_samples: 0,
    confidence_threshold: 0.80,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString()
  },
  
  {
    id: "smell-011",
    name: "Pleurotus ostreatus",
    category: "fungal",
    subcategory: "basidiomycete",
    description: "Oyster mushroom. Mild anise-like undertones with classic mushroom earthiness.",
    bsec_class_id: 0,
    voc_pattern: {
      octanol: 0.40,
      ethanol: 0.25,
      acetaldehyde: 0.15,
      other: 0.20
    },
    icon_type: "mushroom",
    color_hex: "#D3D3D3",
    species_id: "species-pleurotus-ostreatus",
    species_name: "Pleurotus ostreatus",
    training_samples: 0,
    confidence_threshold: 0.80,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString()
  },
  
  {
    id: "smell-012",
    name: "Lentinula edodes",
    category: "fungal",
    subcategory: "basidiomycete",
    description: "Shiitake mushroom. Strong umami with woody, smoky undertones.",
    bsec_class_id: 0,
    voc_pattern: {
      octanol: 0.35,
      ethanol: 0.30,
      acetaldehyde: 0.20,
      other: 0.15
    },
    icon_type: "mushroom",
    color_hex: "#8B4513",
    species_id: "species-lentinula-edodes",
    species_name: "Lentinula edodes",
    training_samples: 0,
    confidence_threshold: 0.80,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString()
  },
  
  {
    id: "smell-020",
    name: "Trichoderma viride",
    category: "fungal",
    subcategory: "contamination",
    description: "Green mold contamination. Coconut-like sweet smell that indicates crop loss.",
    bsec_class_id: 3,
    voc_pattern: {
      ethanol: 0.35,
      acetaldehyde: 0.25,
      other: 0.40
    },
    icon_type: "warning",
    color_hex: "#228B22",
    species_id: "species-trichoderma-viride",
    species_name: "Trichoderma viride",
    training_samples: 0,
    confidence_threshold: 0.70,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString()
  },
  
  // Clean air baseline
  {
    id: "smell-000",
    name: "Clean Air Baseline",
    category: "clean",
    subcategory: "baseline",
    description: "Clean ambient air with no significant VOC signatures. Used as reference.",
    bsec_class_id: -1, // Special: no class detected
    voc_pattern: {
      co2: 0.05,
      other: 0.05
    },
    icon_type: "clean",
    color_hex: "#87CEEB",
    training_samples: 0,
    confidence_threshold: 0.90,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString()
  }
]

// Function to match gas class to smell signature
export function matchSmellByClass(gasClass: number, probability: number): SmellSignature | null {
  const matches = FUNGAL_SMELL_DATABASE.filter(s => s.bsec_class_id === gasClass)
  
  if (matches.length === 0) return null
  
  // Return first match if above threshold
  const match = matches.find(s => probability >= s.confidence_threshold)
  return match || matches[0] // Return first match as fallback
}

// Get all smells in a category
export function getSmellsByCategory(category: string): SmellSignature[] {
  return FUNGAL_SMELL_DATABASE.filter(s => s.category === category)
}

// Get smell by ID
export function getSmellById(id: string): SmellSignature | null {
  return FUNGAL_SMELL_DATABASE.find(s => s.id === id) || null
}

// Search smells by name
export function searchSmells(query: string): SmellSignature[] {
  const lowerQuery = query.toLowerCase()
  return FUNGAL_SMELL_DATABASE.filter(s => 
    s.name.toLowerCase().includes(lowerQuery) ||
    s.description.toLowerCase().includes(lowerQuery) ||
    s.species_name?.toLowerCase().includes(lowerQuery)
  )
}

// Get icon component name for UI
export function getSmellIcon(iconType: SmellSignature["icon_type"]): string {
  const iconMap: Record<string, string> = {
    fungus: "Flower2",
    mushroom: "Flower2",
    mycelium: "Network",
    spore: "Sparkles",
    decay: "Leaf",
    warning: "AlertTriangle",
    plant: "Leaf",
    fire: "Flame",
    chemical: "FlaskConical",
    clean: "Wind"
  }
  return iconMap[iconType] || "HelpCircle"
}
