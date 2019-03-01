function build_icon(master,textNode) {
    var item = document.createElement('i');
    item.className = "material-icons";
    item.appendChild(document.createTextNode(textNode));
    master.appendChild(item);
}

function build_form(master,name,subname1,subname2,subtext,subcls,subtype,callback) {
    var form = document.createElement("form");
    form.setAttribute('id',name);
    form.setAttribute('name',name);
    form.setAttribute('class',"form-horizontal reservation_form");

    var file = build_form_element(subname1,subcls,subtype,"input");
    var submit = build_form_element(subname2,"btn btn-success btn-block","submit","button");
    submit.setAttribute('onclick',callback);
    submit.appendChild(document.createTextNode(subtext));

    var td = document.createElement("td");
    var row = document.createElement("div");
    row.className = "row";

    var element = build_form_div(file);
    row.appendChild(element);
    var element = build_form_div(submit);
    row.appendChild(element);

    form.appendChild(row);
    td.appendChild(form);
    master.appendChild(td);
}

function build_form_element(name,cls,type,elem) {
    var item = document.createElement(elem);
    item.setAttribute('type',type);
    item.setAttribute('class',cls);
    item.setAttribute('id', name);
    item.setAttribute('name', name);
    return item;
}

function build_form_div(element) {
    var div = document.createElement("div");
    div.className = "col-6";
    div.appendChild(element);
    return div;
}