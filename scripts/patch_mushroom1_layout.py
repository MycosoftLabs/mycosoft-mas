#!/usr/bin/env python3
"""
Patches the mushroom1-details.tsx file to replace the old layout section
with the new Control Device Layout.
"""

import re

FILE_PATH = r"C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website\components\devices\mushroom1-details.tsx"

# The new section content to insert
NEW_SECTION = '''          {/* Control Device Layout - Industrial Control Panel Aesthetic */}
          <div className="relative bg-slate-900/50 rounded-3xl border-2 border-amber-500/30 p-6 shadow-2xl shadow-amber-500/5">
            {/* Control Panel Frame */}
            <div className="absolute inset-0 rounded-3xl overflow-hidden pointer-events-none">
              <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-transparent via-amber-500/50 to-transparent" />
              <div className="absolute bottom-0 left-0 right-0 h-1 bg-gradient-to-r from-transparent via-amber-500/30 to-transparent" />
            </div>

            <div className="flex flex-col lg:flex-row gap-6">
              {/* LEFT SIDE: Controller Panel + Description */}
              <div className="lg:w-80 flex flex-col gap-4">
                {/* Controller Panel - Component Selectors */}
                <div className="bg-slate-950 rounded-2xl border border-amber-500/40 p-4 shadow-inner">
                  {/* Panel Header */}
                  <div className="flex items-center gap-2 mb-4 pb-3 border-b border-amber-500/20">
                    <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                    <span className="text-xs font-mono text-amber-400/70 uppercase tracking-wider">Component Selector</span>
                  </div>
                  
                  {/* Component Buttons Grid */}
                  <div className="grid grid-cols-2 gap-2">
                    {DEVICE_COMPONENTS.map((component) => {
                      const IconComponent = component.icon
                      const isSelected = selectedComponent === component.id
                      const isHovered = hoveredComponent === component.id
                      return (
                        <motion.button
                          key={component.id}
                          onClick={() => setSelectedComponent(component.id)}
                          onMouseEnter={() => setHoveredComponent(component.id)}
                          onMouseLeave={() => setHoveredComponent(null)}
                          className={`p-3 rounded-xl border-2 transition-all text-left ${
                            isSelected 
                              ? 'bg-amber-500/20 border-amber-400 shadow-lg shadow-amber-500/30' 
                              : isHovered
                                ? 'bg-amber-500/10 border-amber-500/50'
                                : 'bg-slate-900/50 border-slate-700 hover:border-amber-500/40'
                          }`}
                          whileHover={{ scale: 1.02 }}
                          whileTap={{ scale: 0.98 }}
                        >
                          <div className="flex items-center gap-2">
                            <div className={`p-1.5 rounded-lg ${isSelected ? 'bg-amber-500/30' : 'bg-slate-800'}`}>
                              <IconComponent className={`h-4 w-4 ${isSelected ? 'text-amber-400' : 'text-white/50'}`} />
                            </div>
                            <span className={`text-sm font-medium ${isSelected ? 'text-amber-400' : 'text-white/70'}`}>
                              {component.name}
                            </span>
                          </div>
                          {isSelected && (
                            <motion.div 
                              layoutId="selector-indicator"
                              className="mt-2 h-0.5 bg-gradient-to-r from-amber-400 to-amber-600 rounded-full"
                            />
                          )}
                        </motion.button>
                      )
                    })}
                  </div>
                </div>

                {/* Description Widget - Below Controller */}
                <div className="bg-slate-950 rounded-2xl border border-amber-500/40 p-4 shadow-inner flex-1">
                  {/* Panel Header */}
                  <div className="flex items-center gap-2 mb-3 pb-2 border-b border-amber-500/20">
                    <div className="w-2 h-2 rounded-full bg-amber-500 animate-pulse" />
                    <span className="text-xs font-mono text-amber-400/70 uppercase tracking-wider">Component Details</span>
                  </div>
                  
                  <AnimatePresence mode="wait">
                    {DEVICE_COMPONENTS.filter(c => c.id === selectedComponent).map((component) => (
                      <motion.div
                        key={component.id}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -10 }}
                        transition={{ duration: 0.2 }}
                      >
                        <div className="flex items-center gap-3 mb-3">
                          <div className="p-2 rounded-xl bg-amber-500/20 border border-amber-500/30">
                            <component.icon className="h-6 w-6 text-amber-400" />
                          </div>
                          <div>
                            <h3 className="text-lg font-bold text-amber-400">{component.name}</h3>
                            <p className="text-xs text-white/50 font-mono">{component.description}</p>
                          </div>
                        </div>
                        <p className="text-sm text-white/80 leading-relaxed">{component.details}</p>
                      </motion.div>
                    ))}
                  </AnimatePresence>
                </div>
              </div>

              {/* RIGHT SIDE: Tall Vertical Blueprint */}
              <div className="flex-1 min-w-0">
                <div className="relative h-[700px] bg-slate-950 rounded-2xl border border-amber-500/40 overflow-hidden shadow-inner">
                  {/* Grid pattern */}
                  <div className="absolute inset-0 opacity-15" style={{
                    backgroundImage: `
                      linear-gradient(rgba(251,191,36,0.4) 1px, transparent 1px),
                      linear-gradient(90deg, rgba(251,191,36,0.4) 1px, transparent 1px)
                    `,
                    backgroundSize: '30px 30px'
                  }} />
                  
                  {/* Panel Header */}
                  <div className="absolute top-0 left-0 right-0 p-3 bg-gradient-to-b from-slate-900 to-transparent z-10">
                    <div className="flex items-center gap-2">
                      <div className="w-2 h-2 rounded-full bg-cyan-500 animate-pulse" />
                      <span className="text-xs font-mono text-cyan-400/70 uppercase tracking-wider">Interactive Blueprint</span>
                      <div className="flex-1" />
                      <span className="text-xs font-mono text-white/30">MUSHROOM-1 // REV 2.0</span>
                    </div>
                  </div>
                  
                  {/* Device Blueprint - Vertical orientation */}
                  <div className="absolute inset-0 flex items-center justify-center pt-10">
                    <div className="relative h-[90%] aspect-[3/5] max-w-full">
                      <Image
                        src={MUSHROOM1_ASSETS.mainImage}
                        alt="Mushroom 1 Blueprint"
                        fill
                        className="opacity-40 filter grayscale object-contain"
                      />
                      
                      {/* Interactive component markers */}
                      {DEVICE_COMPONENTS.map((component) => {
                        const isSelected = selectedComponent === component.id
                        const isHovered = hoveredComponent === component.id
                        const isActive = isSelected || isHovered
                        
                        return (
                          <motion.div
                            key={component.id}
                            className="absolute cursor-pointer z-20"
                            style={{ top: component.position.top, left: component.position.left }}
                            onClick={() => setSelectedComponent(component.id)}
                            onMouseEnter={() => setHoveredComponent(component.id)}
                            onMouseLeave={() => setHoveredComponent(null)}
                          >
                            {/* Connection line */}
                            {isSelected && (
                              <motion.div
                                initial={{ opacity: 0, scaleX: 0 }}
                                animate={{ opacity: 1, scaleX: 1 }}
                                className="absolute top-1/2 right-full -translate-y-1/2 w-16 h-px origin-right"
                                style={{ marginRight: '12px' }}
                              >
                                <div className="w-full h-full border-t-2 border-dashed border-amber-400" />
                              </motion.div>
                            )}
                            
                            {/* Marker */}
                            <motion.div
                              className={`w-5 h-5 rounded-full border-2 flex items-center justify-center ${
                                isActive 
                                  ? 'bg-amber-400 border-white shadow-lg shadow-amber-400/50' 
                                  : 'bg-amber-500/40 border-amber-500/50'
                              }`}
                              animate={{
                                scale: isActive ? 1.3 : 1,
                              }}
                              transition={{ duration: 0.2 }}
                            >
                              {isActive && (
                                <motion.div 
                                  className="w-2 h-2 rounded-full bg-white"
                                  animate={{ scale: [1, 0.8, 1] }}
                                  transition={{ duration: 1, repeat: Infinity }}
                                />
                              )}
                            </motion.div>
                            
                            {/* Label on hover */}
                            <AnimatePresence>
                              {isHovered && (
                                <motion.div
                                  initial={{ opacity: 0, x: 10 }}
                                  animate={{ opacity: 1, x: 0 }}
                                  exit={{ opacity: 0, x: 10 }}
                                  className="absolute left-8 top-1/2 -translate-y-1/2 bg-slate-900/95 backdrop-blur-sm px-3 py-1.5 rounded-lg border border-amber-500/30 z-30"
                                >
                                  <span className="text-sm font-medium text-amber-400 whitespace-nowrap">{component.name}</span>
                                </motion.div>
                              )}
                            </AnimatePresence>
                          </motion.div>
                        )
                      })}
                    </div>
                  </div>
                  
                  {/* Bottom status bar */}
                  <div className="absolute bottom-0 left-0 right-0 p-3 bg-gradient-to-t from-slate-900 to-transparent">
                    <div className="flex items-center justify-between text-xs font-mono text-white/30">
                      <span>COMPONENT: <span className="text-amber-400">{DEVICE_COMPONENTS.find(c => c.id === selectedComponent)?.name.toUpperCase()}</span></span>
                      <span className="flex items-center gap-2">
                        <span className="w-1.5 h-1.5 rounded-full bg-green-500" />
                        SYSTEM READY
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>'''

def main():
    # Read file
    with open(FILE_PATH, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find the start marker
    start_marker = '{/* Control Device Layout - Industrial Control Panel Aesthetic */}'
    end_marker = '      </section>\n\n      {/* Mesh Network Visualization */}'
    
    # Find section start
    start_idx = content.find(start_marker)
    if start_idx == -1:
        print("ERROR: Start marker not found!")
        return
    
    # Find where section ends (look for the Mesh Network section)
    mesh_marker = '{/* Mesh Network Visualization */}'
    end_idx = content.find(mesh_marker, start_idx)
    if end_idx == -1:
        print("ERROR: End marker not found!")
        return
    
    # Go back to find the </section> before mesh network
    section_end = content.rfind('      </section>', start_idx, end_idx)
    if section_end == -1:
        print("ERROR: </section> not found!")
        return
    
    # The section to replace goes from start_marker to before the </div> at section_end
    # We need to find the div that ends the blueprint section container
    
    # Actually, let's find the </div>\n        </div>\n      </section> pattern before Mesh
    closing_pattern = '</div>\n        </div>\n      </section>'
    section_close_idx = content.rfind(closing_pattern, start_idx, end_idx)
    if section_close_idx == -1:
        # Try alternative pattern
        closing_pattern = '</div>\n          </div>\n        </div>\n      </section>'
        section_close_idx = content.rfind(closing_pattern, start_idx, end_idx)
    
    print(f"Start index: {start_idx}")
    print(f"Mesh marker index: {end_idx}")
    
    # Get everything between start of section and Mesh Network comment
    # We want to find where the Blueprint section ends
    # Looking for the pattern where the section closes

    # Read line by line to find the section boundary
    lines = content.split('\n')
    start_line = None
    end_line = None
    
    for i, line in enumerate(lines):
        if '{/* Control Device Layout' in line:
            start_line = i
        if '{/* Mesh Network Visualization */}' in line and start_line:
            # End line is 2 lines before this (the </section>)
            end_line = i - 2
            break
    
    if start_line is None or end_line is None:
        print("Could not find section boundaries via line search")
        return
    
    print(f"Start line: {start_line} (0-indexed)")
    print(f"End line: {end_line}")
    
    # Replace lines from start_line to end_line with new section
    new_lines = lines[:start_line]
    new_lines.extend(NEW_SECTION.split('\n'))
    new_lines.extend(lines[end_line + 1:])
    
    new_content = '\n'.join(new_lines)
    
    # Write back
    with open(FILE_PATH, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print("SUCCESS: File patched!")

if __name__ == "__main__":
    main()
