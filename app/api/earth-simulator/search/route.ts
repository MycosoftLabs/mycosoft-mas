import { NextRequest, NextResponse } from "next/server";

/**
 * Search API
 * 
 * Search for locations, species, or observations.
 */

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  
  const query = searchParams.get("q") || "";
  const type = searchParams.get("type") || "all"; // all, location, species, observation

  try {
    if (!query) {
      return NextResponse.json(
        { success: false, error: "Query parameter 'q' is required" },
        { status: 400 }
      );
    }

    const results: any = {
      locations: [],
      species: [],
      observations: [],
    };

    // Search iNaturalist for species and observations
    if (type === "all" || type === "species" || type === "observation") {
      try {
        const response = await fetch(
          `https://api.inaturalist.org/v1/observations?q=${encodeURIComponent(query)}&per_page=50`
        );
        const data = await response.json();
        
        if (data.results) {
          results.observations = data.results.map((obs: any) => ({
            id: obs.id,
            species: obs.species_guess || obs.taxon?.name,
            location: {
              lat: obs.latitude,
              lon: obs.longitude,
            },
            observed_on: obs.observed_on,
            photos: obs.photos?.map((p: any) => ({
              url: p.medium_url || p.url,
            })),
          }));

          // Extract unique species
          const speciesSet = new Set<string>();
          data.results.forEach((obs: any) => {
            const species = obs.species_guess || obs.taxon?.name;
            if (species) speciesSet.add(species);
          });
          results.species = Array.from(speciesSet).map((name) => ({ name }));
        }
      } catch (error) {
        console.error("iNaturalist search error:", error);
      }
    }

    return NextResponse.json({
      success: true,
      query,
      type,
      results,
      count: {
        locations: results.locations.length,
        species: results.species.length,
        observations: results.observations.length,
      },
    });
  } catch (error) {
    console.error("Search error:", error);
    return NextResponse.json(
      {
        success: false,
        error: error instanceof Error ? error.message : "Unknown error",
      },
      { status: 500 }
    );
  }
}
