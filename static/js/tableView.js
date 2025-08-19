function generateTable(watershedData) {
    var dataTableContainer = document.getElementById('dataTableContainer');
    var tableHtml = '<table id="dataTable" class="table table-striped table-bordered"><thead><tr><th>Installation Name</th><th>Name</th><th>QPF Day 1</th><th>QPF Day 2</th><th>QPF Day 3</th></tr></thead><tbody>';

    for (var installationName in watershedData) {
        if (watershedData.hasOwnProperty(installationName)) {
            var shapefiles = watershedData[installationName];
            for (var shapefileName in shapefiles) {
                if (shapefiles.hasOwnProperty(shapefileName)) {
                    var locations = shapefiles[shapefileName];
                    locations.forEach(function(location, index) {
                        var layerId = `${installationName}_${shapefileName}_${index}`;
                        tableHtml += '<tr>';
                        tableHtml += `<td>${installationName.replace('_Watersheds', '')}</td>`;
                        tableHtml += `<td><a href="#" onclick="focusMapOnWatershed('${layerId}'); return false;">${location.name}</a></td>`;
                        tableHtml += '<td>' + location.avg_qpf_day1.toFixed(2) + '</td>';
                        tableHtml += '<td>' + location.avg_qpf_day2.toFixed(2) + '</td>';
                        tableHtml += '<td>' + location.avg_qpf_day3.toFixed(2) + '</td>';
                        tableHtml += '</tr>';
                    });
                }
            }
        }
    }

    tableHtml += '</tbody></table>';
    dataTableContainer.innerHTML = tableHtml;

    // Initialize DataTables on the table
    $(document).ready(function() {
        $('#dataTable').DataTable({
            "pageLength": 100,
            "searching": true,   // Enable the search box
            "ordering": true     // Enable column sorting
        });
    });
}

