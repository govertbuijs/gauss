//////////////////////////////////////////////////////////////////////////////
// Global settings and variables
//////////////////////////////////////////////////////////////////////////////

// Need to specify more
var deviceId;
var logLevel = 1; // 0 = DEBUG, 1 = INFO, 2 = WARN, 3 = ERROR, 4 = OFF
var workerDelay = 1000;
var callWorkerDelay = 250;
var debug = window.location.hostname=='localhost' ||
            window.location.hostname=='gauss_mvp.pulsar.infrae';
var defaultLat = 50.92953250000667;
var defaultLng = 6.968127250671387;

// We need a format function for the URLs, this is horrible
var magnetQuery = '/0/wishcomponent/list/2/';
var magnetAddQuery = '/wish/add/?comp1=1&comp2=2&comp3=';
var magnetDeleteQuery = '/wish/delete/';
var magnetListQuery = '/wish/list/';
var userAddQuery = '/user/add/';
var userSetPosQuery = '/user/setpos/';
var userViewQuery = '/user/get/';
var userUpdateQuery = '/user/update/';
var matchQuery = '/match/list/';
var matchMeetingQuery = '/match/getmeetingspot/';
var actionQuery = '/action/do/';
var pushmessagesQuery = '/pushmessages/list/';
var pushmessagesDeleteQuery = '/pushmessages/delete/';
var chatRoomQuery = '/chat/chatroom/';
var chatWindowQuery = '/chat/window/';
var chatMessageQuery = '/chat/message/';
var chatRoomId;

var googleMap;
var googleMarkerUser;
var googleMarkerMeeting;

var workersTimeout;
var workersDivider = 0;
var callWorkerTimeouts = []
var callQueue = [];
var matchIgnoreList = [];
var matchStatus = [];
var localLog = [];


// device_id, secret and device_os are all mandatory
// secret must be at least 12 characters long.
// device_os must be "iOS".

//////////////////////////////////////////////////////////////////////////////
// Work in progress
//////////////////////////////////////////////////////////////////////////////

// Make actions more instant
// When do we remove the meetingMarker
// Rename log and localLog

//////////////////////////////////////////////////////////////////////////////
// General stuff
//////////////////////////////////////////////////////////////////////////////
function registerHandlers() {
    consoleLog('Registering event handlers', 1);

    // Device ID radio buttons
    $('*[id*=idSelect]').change(selectDeviceId);
    // User wants to add a Magnet
    $('#addMagnet').click(addMagnet);
    // User wants to set it's location
    $('#setLocation').click(setLocation);
    // Give non-developers the opportunity to view localLogs
    $("#toggleLocalLog").click(toggleLocalLogs);
    // User wants to send a chat message
    $("#chatSend").click(sendChatMessage);
}

function selectDeviceId(obj) {
    deviceId = obj.target.value;
    cleanupOldUser();
    getUserInfo(loadMagnetList);
    showUI()
}

function cleanupOldUser() {
    consoleLog('Cleaning old user data', 1);

    // Clean status data
    callQueue = [];
    matchIgnoreList = [];
    matchStatus = [];
    localLog = [];

    // Remove messages
    $("#messageList").find("div").remove();
    // Remove matches
    $("#matchTable").find("tr:gt(0)").remove();
    // Remove log entries
    $("#messageList").find("div").remove();
    // Remove chats
    $("#chatList").find("div").remove();
}

function showUI() {
    $('#left').css('display', 'block');
    $('#middle').css('display', 'block');
    $('#right').css('display', 'block');
    $('#content1').css('display', 'block');
    if (debug) {
        $('#content2').css('display', 'block');
    } else {
        $('#toggleLocalLog').css('display', 'block');
    }
    $('#footer').css('display', 'block');
    google.maps.event.trigger(googleMap, 'resize');
}

function toggleLocalLogs() {
    if ($('#content2').css('display')=='none') {
        $('#content2').css('display', 'block');
    } else {
        $('#content2').css('display', 'none');
    }
}

function workerFunction() {
    workersDivider += 1;
    if (workersDivider > 4) {
        workersDivider = 0;
    }
     
    // Run every 5 seconds
    if (workersDivider == 0) {
        getMatchList();
        getPushMessages();
    }
    // Run every second
    displayLocalLog();
    getChatMessages();
    
    workersTimeout = setTimeout(workerFunction, workerDelay);
}

$(document).ready(function() {
    consoleLog('Document ready', 1);

    // Static initialization
    registerHandlers();
    loadMagnets();
    setupGoogleMap();

    // Dynamic initialization
    // XXX TODO Only need 1 callWorker for now, lookup max for each browser
    callWorker(callWorkerTimeouts[0]);
    workerFunction();

    // XXX TODO We need a supervisor worker
});

//////////////////////////////////////////////////////////////////////////////
// MVP API stuff
//////////////////////////////////////////////////////////////////////////////
function callWorker(callWorkerTimeout) {
    clearTimeout(callWorkerTimeout);

    function doAjaxCall(item) {
        $.ajax({
            type: 'GET',
            url: item[0],
            dataType: 'json',
            success: item[1],
            error: item[2],
            complete: function(jqXHR, textStatus) {
                callWorkerTimeout = setTimeout(callWorker, callWorkerDelay, callWorkerTimeout);
            },
        });
    }

    try {
        var item = callQueue.splice(0, 1)[0];
        if (item.length < 3) {
            item[2] = ajaxError;
        }
        doAjaxCall(item);
    } catch(err) {
        callWorkerTimeout = setTimeout(callWorker, callWorkerDelay, callWorkerTimeout);
    }
}

// XXX TODO Retrieve token ??
function getUserInfo(func) {
    var url = '/' + deviceId + userViewQuery + deviceId + '/';
    consoleLog('Getting user info for deviceId ' + deviceId, 1);
    callQueue.push([url, successFunction]);
 
    function successFunction(data, textStatus, jqXHR) {
        // Clean input fields
        $('#latInput').val('');
        $('#lonInput').val('');

        if (data.Success =='True') {
            var lat = data['latitude'];
            var lon = data['longitude'];
    
            if (lat!=0 || lon!=0) { 
                var latlng = new google.maps.LatLng(lat, lon);

                placeUserMarker(latlng);
                googleMap.setCenter(latlng);

                $('#latInput').val(lat);
                $('#lonInput').val(lon);
            } else {
                removeUserMarker();
            }
        } else {
            addUser();
        }
        func();
    }       
}

function addUser() {
    var url = '/' + deviceId + userAddQuery;
    consoleLog('Checking user for deviceId ' + deviceId, 1);
    callQueue.push([url, successFunction]);

    function successFunction(data, textStatus, jqXHR) {
        if (data.Success == 'True') {
            consoleLog("User with deviceId = " + deviceId + " added", 1); 
        } else {
            consoleLog(data.Error, 0); 
        }
    }
}

function setLocation() {
    var lat = $('#latInput').val();
    var lon = $('#lonInput').val();
    var url = '/' + deviceId + userSetPosQuery + lat + ',' + lon + '/';
    
    if (typeof deviceId === "undefined") { return }
    if ((lat=='') || (lon=='') ) { return }

    consoleLog("Setting location to " + lat + ', ' + lon + "for device " + deviceId, 1);
    callQueue.push([url, successFunction]);

    function successFunction(data, textStatus, jqXHR) {
        if (data.Success == 'True') {
            consoleLog("User position set for device " + deviceId, 1);
            logLocalAction('setLocation' + lat +' : '+ lon);
        } else {
            consoleLog(data.Error, 0); 
        }
    }
}

function loadMagnets() {
    var url = magnetQuery;
    consoleLog("Loading Magnets from " + url, 1);
    callQueue.push([url, successFunction]);

    function successFunction(data, textStatus, jqXHR) {
        consoleLog('Loaded magnets', 1);

        $('#magnetSelect').find('option').remove();
        results = data.Results;
        for (result in results) {
            result = results[result];
            var option = '<option value="' + result.id + '">' + result.name + '</option>';
            $(option).appendTo('#magnetSelect'); 
        }
    }
}

function addMagnet() {
    var magnetId = $('#magnetSelect').val();
    var url = '/' + deviceId + magnetAddQuery + magnetId;
    consoleLog("Adding magnet " + magnetId + " for device " + deviceId, 1);
    callQueue.push([url, successFunction]);

    function successFunction(data, textStatus, jqXHR) {
        if (data.Success == 'True') {
            consoleLog(data.Message, 1); 
            logLocalAction('addMagnet ' + magnetId);
        } else {
            consoleLog(data.Error, 1); 
        }
        loadMagnetList();
    }

    if (typeof deviceId === "undefined") {
        return
    }
}

function removeMagnet(obj) {
    var url = '/' + deviceId + magnetDeleteQuery + obj.data + '/';
    consoleLog("Deleting Magnet " + obj.data + " for device " + deviceId, 1);
    callQueue.push([url, successFunction]);

    function successFunction(data, textStatus, jqXHR) {
        if (data.Success == 'True') {
            consoleLog(data.Message, 0); 
            logLocalAction('removeMagnet ' + obj.data);
        } else {
            consoleLog("Error deleting Magnet " + obj.data + " for device " + deviceId, 1);
        }
        loadMagnetList();
    }
}

function loadMagnetList() {
    var url = '/' + deviceId + magnetListQuery;
    consoleLog("Loading MagnetList for device " + deviceId + " from " + url, 1);
    callQueue.push([url, successFunction]);

    function successFunction(data, textStatus, jqXHR) {
        // Clear the old list
        $("#magnetTable").find("tr:gt(0)").remove();
            
        if (data.Success == 'True') {
            // Fill the list with found values
            for (result in data.Results) {
                result = data.Results[result];
                $('<tr>')
                    .append( $('<td>').html(result[3]).attr('colspan', 2) )
                    .append( $('<button>').attr('id', 'removeMagnet' + result['id'])
                        .click(result['id'], removeMagnet).attr('type', 'button').text('X'))
                    .appendTo('#magnetTable');
            }
            consoleLog("Loaded MagnetList for device " + deviceId, 1);
        } else {
            consoleLog("No Magnets listed for device " + deviceId, 1); 
        }
    }
}

function matchAction(obj) {
    if (obj.data[1] == 'ignore') {
        matchIgnoreList.push(obj.data[2]);
        return;
    }

    var url = '/' + deviceId + actionQuery + obj.data[0] + '/?reply=' + obj.data[1];
    consoleLog('MatchAction ' + obj.data[0] +' : '+ obj.data[1], 1);
    callQueue.push([url, successFunction]);

    function successFunction (data, textStatus, jqXHR) {
        if (data.Success == 'True') {
            consoleLog("User with deviceId = " + deviceId + " added", 1); 
            logLocalAction('matchAction' + obj.data[0] +' : '+ obj.data[1]);
        } else {
            consoleLog(data.Error, 0); 
        }
    }
}

function getMatchList() {
    if (typeof deviceId === "undefined") { return }

    var url = '/' + deviceId + matchQuery;
    consoleLog('Getting match list for deviceId ' + deviceId, 1);
    callQueue.push([url, successFunction]);
        
    function successFunction (data, textStatus, jqXHR) {
        // Clear the old list
        $("#matchTable").find("tr:gt(0)").remove();

        if (data.Success =='True') {
            for (result in data.Results) {
                result = data.Results[result];
                if (matchIgnoreList.indexOf(result.id) > -1) { continue; }

                // XXX TODO Move this to a separate function??
                if (result.suggestion=='meeting' && result.your_status=='accepted') {
                    getMeetingLocation(result.id);
                    matchIgnoreList.push(result.id);

                    // Just clear the table in stead fo waiting, looks nicer
                    $("#matchTable").find("tr:gt(0)").remove();
                    continue;
                } else if (result.suggestion=='chat' && result.your_status=='accepted') {
                    getRoomId(result.id);
                    matchIgnoreList.push(result.id);

                    // Just clear the table in stead fo waiting, looks nicer
                    $("#matchTable").find("tr:gt(0)").remove();
                    continue;
                }

                var status = {  'pendingaction': result.pendingaction,
                                'pendingactionid':result.pendingactionid,
                                'suggestion': result.suggestion,
                                'wishid': result.wishid,
                                'your_status': result.your_status, };
                matchStatus[result.id] = status;
                
                var row = $('<tr>').append( $('<td>').html(result.wish) );

                for (buttonId in result['buttons']) {
                    button = result['buttons'][buttonId];
                    var btn = $('<button>').attr('id', button.key +'_'+ buttonId)
                        .text(button.label).click(matchAction)

                    $('<td>').append(
                        $('<button>').attr('id', button.key +'_'+ result.id).text(button.label)
                        .click([result.pendingactionid, button.key, result.id], matchAction)
                        ).appendTo(row);
                }

                row.appendTo('#matchTable');

                // XXX TODO Remove below, only for testing
                if (debug) {
                    $('<tr>')
                        .append( $('<td>').html('id') )
                        .append( $('<td colspan="2">').html(result.id) )
                        .appendTo('#matchTable');
                    $('<tr>')
                        .append( $('<td>').html('pendingaction') )
                        .append( $('<td colspan="2">').html(result.pendingaction) )
                        .appendTo('#matchTable');
                    $('<tr>')
                        .append( $('<td>').html('pendingactionid') )
                        .append( $('<td colspan="2">').html(result.pendingactionid) )
                        .appendTo('#matchTable');
                    $('<tr>')
                        .append( $('<td>').html('suggestion') )
                        .append( $('<td colspan="2">').html(result.suggestion) )
                        .appendTo('#matchTable');
                    $('<tr>')
                        .append( $('<td>').html('wishid') )
                        .append( $('<td colspan="2">').html(result.wishid) )
                        .appendTo('#matchTable');
                    $('<tr>')
                        .append( $('<td>').html('your_status') )
                        .append( $('<td colspan="2">').html(result.your_status) )
                        .appendTo('#matchTable');
                }
            }
        } else {
            consoleLog(data.Error, 0);
        }
    }
}

function getMeetingLocation(matchId) {
    var url = '/' + deviceId + matchMeetingQuery + matchId + '/';
    consoleLog('Getting meetingpoint for matchId ' + matchId, 1);
    callQueue.push([url, successFunction]);

    function successFunction (data, textStatus, jqXHR) {
        if (data.Success == 'True') {
            if (data.results.name) {
                var place = data.results
                var latlng = new google.maps.LatLng(place.geometry.location.lat, place.geometry.location.lng);
                placeMeetingMarker(latlng, place.name);
            } else {
                // XXX TODO Show user?
                consoleLog('Sorry, no meeting spot found', 1);
            }
        } else {
            consoleLog(data.Error, 0); 
        }
    }

}

function getPushMessages() {
    if (typeof deviceId === "undefined") { return }

    var url = '/' + deviceId + pushmessagesQuery;
    consoleLog('Checking pushmessages for deviceId ' + deviceId, 1);
    callQueue.push([url, successFunction]);

    function successFunction (data, textStatus, jqXHR) {
        if (data.Success == 'True') {
            for (message in data.Messages) {
                $('<div>').html(data.Messages[message].message + ', PARAS: ' +  data.Messages[message].params).appendTo('#messageList');
            }
        } else {
            consoleLog(data.Error, 0); 
        }
    }
}

function getRoomId(matchId) {
    var url = chatRoomQuery + matchId + '/';
    consoleLog('Getting roomId match ' + matchId, 1);
    callQueue.push([url, successFunction]);

    function successFunction (data, textStatus, jqXHR) {
        if (data.Success == 'True') {
            chatRoomId = data.Roomid;
            showChatWindow();
        } else {
            consoleLog(data.Error, 0); 
        }
    }
}

function sendChatMessage() {
    if (typeof chatRoomId === "undefined") { return }
    
    var message = $('#chatInput').val();
    if (message.length < 1) { return }

    message = escape(message);
    var url = chatMessageQuery + deviceId +'/'+ chatRoomId +'/'+ message +'/';
    consoleLog('Sending message '+ message +' to room ' + chatRoomId, 1);
    callQueue.push([url, successFunction]);

    function successFunction (data, textStatus, jqXHR) {
        // Empty input
        $('#chatInput').val('');

        if (data.Success == 'False') {
            consoleLog(data.Error, 0); 
        }
    }
}

function getChatMessages() {
    if (chatRoomId == undefined) { return }

    var url = chatWindowQuery + deviceId +'/'+ chatRoomId + '/';
    callQueue.push([url, successFunction]);
    consoleLog('Getting messages for room ' + chatRoomId, 1);

    function successFunction (data, textStatus, jqXHR) {
        if (data.Success == 'True') {
            // Clear div
            $("#chatList").find("div").remove();
          
            // Fill div
            for (message in data.Messages) {
                $('<div>').html(data.Messages[message]).appendTo('#chatList');

                if (data.Messages[message] == 'This connection is suspended') {
                    disableChatSend();
                }
            }
        } else {
            // Check if we are still allowed to enter things 
            if ((data.Messages.length==1) && (data.Messages[0]=='This connection has timed out')) {
                closeChatWindow();
            } else {
                consoleLog(data.Error, 0);
            }
        }
    }
}

function disableChatSend() {
    $("#chatSend").attr("disabled", "true");
    $("#chatInput").attr("disabled", "true");
}

function showChatWindow() {
    consoleLog('Show chat window', 1);

    if (chatRoomId == undefined) { return }
    $("#chatSend").removeAttr("disabled");
    $("#chatInput").removeAttr("disabled");
    $('#content0').css('display', 'block');
}

function closeChatWindow() {
    consoleLog('Close chat window', 1);

    $("#chatList").find("div").remove();
    $('#content0').css('display', 'none');
    chatRoomId = undefined;
}

//////////////////////////////////////////////////////////////////////////////
// Google Maps stuff
//////////////////////////////////////////////////////////////////////////////
function setupGoogleMap() {
    var latlng = new google.maps.LatLng(defaultLat, defaultLng);
    var mapOptions = {
        zoom: 10,
        mapTypeId: google.maps.MapTypeId.ROADMAP,
        center: latlng
    };

    googleMap = new google.maps.Map(document.getElementById("googleMap"), mapOptions);

    google.maps.event.addListener(googleMap, 'click', function(event) {
        placeUserMarker(event.latLng);
    });
};

function placeUserMarker(location) {
    if (googleMarkerUser == undefined) {
        markerOptions = { position: location, map: googleMap, title:"You are here!", };
        googleMarkerUser = new google.maps.Marker(markerOptions);
    } else {
        googleMarkerUser.setPosition(location);
    }
}

function removeUserMarker() {
    consoleLog('Removing the user marker', 1);
    if (googleMarkerUser != undefined) {
        googleMarkerUser.setMap(null);
        googleMarkerUser = undefined;
    }
}
function placeMeetingMarker(location, title) {
    removeMeetingMarker();
    googleMap.setCenter(location);
    googleMap.setZoom(16);

    if (googleMarkerMeeting == undefined) {
        var image = "/static_media/images/meeting_marker.png";
        markerOptions = { position: location, map: googleMap, 
                          title: title, icon: image, zIndex: 1000,
                          animation: google.maps.Animation.DROP, };
        googleMarkerMeeting = new google.maps.Marker(markerOptions);
    } else {
        googleMarkerMeeting.setPosition(location);
    }
}

function removeMeetingMarker() {
    consoleLog('Removing the meeting marker', 1);
    if (googleMarkerMeeting != undefined) {
        googleMarkerMeeting.setMap(null);
        googleMarkerMeeting = undefined;
    }
}
//////////////////////////////////////////////////////////////////////////////
// Helper functions
//////////////////////////////////////////////////////////////////////////////
function consoleLog(message, level) {
    if (level >= logLevel) {
        console.log(message);
    }
}

function ajaxError(xhr, status) {
    consoleLog(status, 5);
}

function displayLocalLog() {
    // Empty the div
    $("#localLog").find("div").remove();

    // Fill the div
    for (entry in localLog) {
        $('<div>').html(localLog[entry]['time'] +' | '+ localLog[entry]['message']).appendTo('#localLog');
    }
}

function logLocalAction(message) {
    var cur = new Date();
    var hours = cur.getHours() < 10 ? '0' + cur.getHours() : cur.getHours();
    var minutes = cur.getMinutes() < 10 ? '0' + cur.getMinutes() : cur.getMinutes();
    var seconds = cur.getSeconds() < 10 ? '0' + cur.getSeconds() : cur.getSeconds();
    var time = hours +':'+ minutes +':'+ seconds;

    localLog.push( { 'time': time, 'message': message });
}

//////////////////////////////////////////////////////////////////////////////
// Old
//////////////////////////////////////////////////////////////////////////////

// http://stackoverflow.com/questions/105034/how-to-create-a-guid-uuid-in-javascript
