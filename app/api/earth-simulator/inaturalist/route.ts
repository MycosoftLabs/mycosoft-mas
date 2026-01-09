import { NextRequest, NextResponse } from "next/server";
import { inaturalistClient } from "@/lib/inaturalist-client";

/**
 * iNaturalist API Proxy
 * 
 * Fetches organism observations from iNaturalist API.
 * Focuses on fungal/mushroom observations for mycelium mapping.
 */

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  
  const action = searchParams.get("action") || "search";
  const lat = parseFloat(searchParams.get("lat") || "0");
  const lng = parseFloat(searchParams.get("lng") || "0");
  const radius = parseFloat(searchParams.get("radius") || "1000"); // meters
  const nelat = parseFloat(searchParams.get("nelat") || "0");
  const nelng = parseFloat(searchParams.get("nelng") || "0");
  const swlat = parseFloat(searchParams.get("swlat") || "0");
  const swlng = parseFloat(searchParams.get("swlng") || "0");
  const taxonId = searchParams.get("taxon_id") ? parseInt(searchParams.get("taxon_id")!) : undefined;
  const observedOn = searchParams.get("observed_on") || undefined;
  const perPage = parseInt(searchParams.get("per_page") || "200");

  try {
    let observations;

    switch (action) {
      case "fungi":
        // Get fungal observations (Kingdom Fungi = 47170)
        observations = await inaturalistClient.getFungalObservations({
          lat,
          lng,
          radius,
          observed_on: observedOn,
          per_page: perPage,
        });
        break;

      case "bounds":
        // Get observations in bounding box
        observations = await inaturalistClient.getObservationsInBounds({
          nelat,
          nelng,
          swlat,
          swlng,
          taxon_id: taxonId || 47170, // Default to fungi
          observed_on: observedOn,
          per_page: perPage,
        });
        break;

      case "search":
      default:
        // General search
        const response = await inaturalistClient.searchObservations({
          lat,
          lng,
          radius,
          taxon_id: taxonId,
          quality_grade: "research",
          observed_on: observedOn,
          per_page: perPage,
        });
        observations = response.results || [];
        break;
    }

    return NextResponse.json({
      success: true,
      action,
      observations: observations.map((obs) => ({
        id: obs.id,
        observed_on: obs.observed_on,
        latitude: obs.latitude,
        longitude: obs.longitude,
        species: obs.species_guess || obs.taxon?.name,
        taxon_id: obs.taxon_id || obs.taxon?.id,
        taxon: obs.taxon,
        photos: obs.photos?.map((p) => ({
          id: p.id,
          url: p.medium_url || p.url,
          license: p.license_code,
        })),
        quality_grade: obs.quality_grade,
        user: obs.user?.login,
      })),
      count: observations.length,
    });
  } catch (error) {
    console.error("iNaturalist API error:", error);
    return NextResponse.json(
      {
        success: false,
        error: error instanceof Error ? error.message : "Unknown error",
      },
      { status: 500 }
    );
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { action, params } = body;

    let observations;

    switch (action) {
      case "fungi":
        observations = await inaturalistClient.getFungalObservations({
          lat: params.lat,
          lng: params.lng,
          radius: params.radius || 1000,
          observed_on: params.observed_on,
          per_page: params.per_page || 200,
        });
        break;

      case "bounds":
        observations = await inaturalistClient.getObservationsInBounds({
          nelat: params.nelat,
          nelng: params.nelng,
          swlat: params.swlat,
          swlng: params.swlng,
          taxon_id: params.taxon_id || 47170,
          observed_on: params.observed_on,
          per_page: params.per_page || 200,
        });
        break;

      default:
        return NextResponse.json(
          { success: false, error: `Unknown action: ${action}` },
          { status: 400 }
        );
    }

    return NextResponse.json({
      success: true,
      action,
      observations: observations.map((obs) => ({
        id: obs.id,
        observed_on: obs.observed_on,
        latitude: obs.latitude,
        longitude: obs.longitude,
        species: obs.species_guess || obs.taxon?.name,
        taxon_id: obs.taxon_id || obs.taxon?.id,
        photos: obs.photos?.map((p) => ({
          id: p.id,
          url: p.medium_url || p.url,
        })),
      })),
      count: observations.length,
    });
  } catch (error) {
    console.error("iNaturalist API error:", error);
    return NextResponse.json(
      {
        success: false,
        error: error instanceof Error ? error.message : "Unknown error",
      },
      { status: 500 }
    );
  }
}
