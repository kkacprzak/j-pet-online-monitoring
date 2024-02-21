function buildListElement(filename){
    var file_entry = document.createElement("li");
    file_entry.innerHTML = `<a href="monitoring.htm?filename=${filename}">${filename}</a>`;
    document.getElementById("file_list").appendChild(file_entry);    
}

const request = async() => {

    var myRequest = new Request('files.json');
    
    // required to avoid caching of the file
    var myHeaders = new Headers();
    myHeaders.append('pragma', 'no-cache');
    myHeaders.append('cache-control', 'no-cache');
    
    var myInit = {
	method: 'GET',
	headers: myHeaders,
    };

    const response = await fetch(myRequest, myInit);
    const json = await response.json()
    json["files"].sort(function(a, b){return b-a}).forEach(buildListElement);

    var list = json["files"].sort(function(a, b){return b-a});
    var last_filename = list[list.length-1];
    var file_entry = document.createElement("li");
    file_entry.innerHTML = `<a href="monitoring.htm?filename=${last_filename}">${last_filename}</a>`;
    document.getElementById("most_recent_file_list").appendChild(file_entry);    
}

request();
