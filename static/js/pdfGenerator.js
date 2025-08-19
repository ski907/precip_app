function generatePDF() {
    const { jsPDF } = window.jspdf;
    const doc = new jsPDF();
    
    // Title
    doc.setFontSize(16);
    doc.text('Precipitation Forecast Report', 14, 20);
    
    // Date
    doc.setFontSize(10);
    const today = new Date().toLocaleDateString();
    doc.text(`Generated: ${today}`, 14, 30);
    
    // Temporarily add all forecast layers for screenshot
    const originalLayers = [];
    for (let day in forecastLayers) {
        if (!map.hasLayer(forecastLayers[day])) {
            map.addLayer(forecastLayers[day]);
            originalLayers.push(day);
        }
    }
    
    // Wait longer for tiles to load properly
    setTimeout(() => {
        // Store current map center to restore later
        const originalCenter = map.getCenter();
        const originalZoom = map.getZoom();
        
        // Shift map east (increase longitude)
        const shiftedCenter = [originalCenter.lat, originalCenter.lng + 75]; // Adjust as needed
        map.setView(shiftedCenter, originalZoom);
        
        // Force map to refresh and load all tiles
        map.invalidateSize();
        
        // Wait a bit more for tiles to fully load
        setTimeout(() => {
            // Capture the map using dom-to-image
            domtoimage.toPng(document.getElementById('map'), {
                width: 800,
                height: 500,
                style: {
                    'transform': 'scale(1)',
                    'transform-origin': 'top left'
                }
            }).then(function(dataUrl) {
                // Restore original map center
                map.setView(originalCenter, originalZoom);
                
                // Add map image to PDF
                doc.addImage(dataUrl, 'PNG', 14, 40, 180, 113);
                
                // Remove temporarily added layers
                originalLayers.forEach(day => {
                    map.removeLayer(forecastLayers[day]);
                });
                
                // Continue with table generation
                generateTableForPDF(doc, 160);
            }).catch(function(error) {
                console.error('Error capturing map:', error);
                // Restore original map center even on error
                map.setView(originalCenter, originalZoom);
                
                // Continue without map image
                generateTableForPDF(doc, 40);
                
                // Remove temporarily added layers
                originalLayers.forEach(day => {
                    map.removeLayer(forecastLayers[day]);
                });
            });
        }, 2000);
    }, 1000);
}

function generateTableForPDF(doc, startY) {
    // Prepare data - only locations with precipitation > 0
    const tableData = [];
    for (var installationName in watershedData) {
        if (watershedData.hasOwnProperty(installationName)) {
            var shapefiles = watershedData[installationName];
            for (var shapefileName in shapefiles) {
                if (shapefiles.hasOwnProperty(shapefileName)) {
                    var locations = shapefiles[shapefileName];
                    locations.forEach(function(location) {
                        // Only include if any day has precipitation > 0
                        if (location.avg_qpf_day1 > 0 || location.avg_qpf_day2 > 0 || location.avg_qpf_day3 > 0) {
                            tableData.push([
                                installationName.replace('_Watersheds', ''),
                                location.name,
                                {
                                    content: location.avg_qpf_day1.toFixed(2),
                                    styles: location.avg_qpf_day1 > 0.01 ? { fontStyle: 'bold' } : {}
                                },
                                {
                                    content: location.avg_qpf_day2.toFixed(2),
                                    styles: location.avg_qpf_day2 > 0.01 ? { fontStyle: 'bold' } : {}
                                },
                                {
                                    content: location.avg_qpf_day3.toFixed(2),
                                    styles: location.avg_qpf_day3 > 0.01 ? { fontStyle: 'bold' } : {}
                                }
                            ]);
                        }
                    });
                }
            }
        }
    }
    
    // Generate table
    doc.autoTable({
        head: [['Installation', 'Location', 'Day 1 QPF', 'Day 2 QPF', 'Day 3 QPF']],
        body: tableData,
        startY: startY,
        styles: {
            fontSize: 9,
            cellPadding: 3
        },
        headStyles: {
            fillColor: [66, 139, 202],
            textColor: 255,
            fontStyle: 'bold'
        },
        alternateRowStyles: {
            fillColor: [240, 240, 240]
        }
    });
    
    // Save the PDF
    const today = new Date().toLocaleDateString();
    doc.save(`precipitation-forecast-${today.replace(/\//g, '-')}.pdf`);
}