function findGetParameter(parameterName) {
    var result = null,
	tmp = [];
    location.search
        .substr(1)
        .split("&")
        .forEach(function (item) {
	    tmp = item.split("=");
	    if (tmp[0] === parameterName) result = decodeURIComponent(tmp[1]);
	});
    return result;
}

function readHisto(file_name, full_histo_name, callback){
    JSROOT.OpenFile(file_name, function(file){	
        file.ReadObject(full_histo_name, function(histo){
	    callback(histo);
        });
    });
}

function constructPlot(plot_desc){
    
    const title = plot_desc["Title"].replace(/ /g,"_");;
    
    var top_div = document.createElement("div");
    top_div.style.cssText = "background: lightgray; margin: 10px";
    top_div.innerHTML = `
        <h2>${plot_desc["Title"]}</h2>
	<div style="display: flex">
	<div id="plot_${title}" style="width: 600px; height: 550px; margin: 10px; display: inline-block;">
       	<h3>Current plot</h3>
	</div>
	<div id="plot_description_${title}" style="margin: 30px; width: 600px; height: 550px; display: inline-block;">
	<h3>Description</h3>
	${plot_desc["Description"]}
	<h3>Obtained with selection criteria:</h3>
	${plot_desc["Selection criteria"]}
        </div>
	<div id="plot_reference_${title}" style="width: 600px; height: 550px; margin: 10px; display: inline-block;">
       	<h3>Reference plot</h3>
	</div>
    </div>
	`
    document.getElementById("monitoring_plots").appendChild(top_div);

    // add also to table of contents
    var toc_entry = document.createElement("li");
    toc_entry.innerHTML = `<a href="#plot_${title}">${plot_desc["Title"]}</a>`;
    document.getElementById("toc").appendChild(toc_entry);
    
    // add current plot
    let full_histo_name = plot_desc["Directory"] + "/" + plot_desc["Histo"];
    let root_file_name = findGetParameter("filename");
    readHisto("rootfiles/" + root_file_name, full_histo_name, function(histo){
    	JSROOT.draw("plot_" + title, histo, plot_desc["Options"] );
    });

    // add reference plot
    readHisto("rootfiles/reference/reference.root", full_histo_name, function(histo){
    	JSROOT.draw("plot_reference_" + title, histo, plot_desc["Options"] );
    });
}
	
function constructPlots(desc){
    desc.forEach(plot_desc => constructPlot(plot_desc));	
}

function startGUI() {
    
    // load descriptions from config file
    var myRequest = new Request('description.json');
    
    // required to avoid caching of the descriptionsfile 
    var myHeaders = new Headers();
    myHeaders.append('pragma', 'no-cache');
    myHeaders.append('cache-control', 'no-cache');
    
    var myInit = {
	method: 'GET',
	headers: myHeaders,
    };
    
    var desc = fetch(myRequest, myInit)
 	.then(response => response.json())
 	.then(function(json){
	    constructPlots(json["Plots"]);
	}
	     );
    
}

startGUI();
