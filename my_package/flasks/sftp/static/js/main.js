function download_file() {
    var urlParams = new URLSearchParams(window.location.search)
    $.ajax({
        url:'/api/v2/directory',
        type:'get',
        data: {
            path: urlParams.get('path') || "."
        },
        timeout: 30000,
        error: function(){
            show_msg("Не удалось скачать файл. Сервер ответил: " + this.status,"alert alert-danger");
        },
        success:function(result){
            window.location = '/api/v2/directory?path=' + urlParams.get('path')
        }
    });
}

function show_msg(msg, cls) {
    var master = document.getElementById('messenger');
    var row = document.createElement("div");
    row.className = "row";

    var node = document.createElement("div");
    if (cls) {
        node.className = cls;
    } else {
        node.className = "alert alert-primary";
    }

    var textnode = document.createTextNode(msg);
    node.appendChild(textnode);
    row.appendChild(node);
    master.insertBefore(row, null);

    setTimeout(function(obj){
        var master = document.getElementById("messenger");
        master.removeChild(obj);
    }, 5000, row);
}

function delete_file() {
    var urlParams = new URLSearchParams(window.location.search)
    $.ajax({
        url:'/api/v2/directory?path=' + urlParams.get('path'),
        type:'delete',
        timeout: 30000,
        error: function(){
            show_msg("Не удалось удалить файл|директорию. Сервер ответил: " + this.status,"alert alert-danger");
        },
        success:function(result){
            show_msg("Файл(Директория) был успешно удален: " + urlParams.get('path'),"alert alert-danger");
            var path = urlParams.get('path');
            var pathSplit = path.split('\\');
            var newPath;
            if (pathSplit.length == 1) {
                newPath = '.';
            } else {
                newPath = pathSplit.slice(0,-1).join('\\');
            }
            urlParams.set('path', newPath);
            window.location.search = urlParams.toString();
        }
    });
}

function sync(btn) {
    var remove_flag = document.getElementById("approve_delete");
    var action;
    if (btn.id == 'send_btn') {
        action = 'from';
    } else if (btn.id == 'resv_btn') {
        action = 'to';
    }

    $.ajax({
        url:'/api/v2/directory/sync',
        type:'post',
        data: {
            action: action,
            remove: remove_flag.checked
        },
        timeout: 30000,
        beforeSend: function(){
            show_msg("Ничего не трогайте, мы начали синхронизацию.","alert alert-info");
            var btn1 = document.getElementById('send_btn');
            btn1.disabled = true;
            var btn2 = document.getElementById('resv_btn');
            btn2.disabled = true;
        },
        error: function(){
            show_msg("Не удалось синхронизировать директорию. Сервер ответил: " + this.status,"alert alert-danger");
        },
        success:function(result){
            show_msg(result['description'],result['class_description']);
            getTree(false);
        },
        complete:function(){
            var btn1 = document.getElementById('send_btn');
            btn1.disabled = false;
            var btn2 = document.getElementById('resv_btn');
            btn2.disabled = false;
        }
    });
}