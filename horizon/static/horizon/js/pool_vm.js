var Pool_id = ""
var tenant_id=document.getElementById("tenant_id").value;
function bind_vm(){
    var Data=""
    var noBindVm_list=""
    var obj_noBind= new Array()
    var text = document.getElementById("oneKeyBinding").innerText
    //$("#nobind_VM ul").each(function(i,dom){
    //    noBindVm_list += dom.id + ","
    //});
    if(text == "Bindings"){
	$("#nobind_VM ul").each(function(i,dom){
            noBindVm_list += dom.id + ","
        });
        obj_noBind = noBindVm_list.substring(0,noBindVm_list.length - 1).split(',')
        for(var i=0;i<obj_noBind.length;i++){
            Data += "\"" + obj_noBind[i] +"\","
        }
        Data = "[" + Data.substring(0,Data.length - 1) + "]"
        bind_all_float_vm(Data);
    }
    if(text == "Remove"){
	$("#User_VM ul").each(function(i,dom){
            noBindVm_list += dom.id + ","
        });
        obj_noBind = noBindVm_list.substring(0,noBindVm_list.length - 1).split(',')
        for(var i=0;i<obj_noBind.length;i++){
            Data += "\"" + obj_noBind[i] +"\","
        }
        Data = "[" + Data.substring(0,Data.length - 1) + "]"
        remove_all_float_vm(Data);
    }
}

function bind_all_float_vm(dataStr){
show();
$.ajax({
    type:"GET",
    url: "/dashboard/admin/projects/"+ Pool_id +"/pool_bindvm_ajax/",
    data:{"data":dataStr},
    dataType:"jsonp",
    jsonp:"callback",
    jsonpCallback:"match",
    success:function(data){
        var newData = data.success
        Close_Div();
        if(newData){
        for(var i=0;i < newData.length;i++){
            $('#nobind_VM>ul[id='+ newData[i][1] + ']').remove();
        }
        for(var i=0;i<newData.length;i++){
            var Div_id = document.getElementById("User_VM");
            var ul = document.createElement("ul");
            ul.setAttribute("id", newData[i][1]);
            ul.innerHTML = "<li id=\"\" style=\"width: 85%;float: left\">"+newData[i][0]+"</li>" +
	    "<a  href=\"javascript:remove_pool_vm(\'"+newData[i][1]+"\',\'"+ newData[i][0]+"\')\" class=\"btn-primary\" style=\"text-decoration:none;\">-</a>";
            Div_id.appendChild(ul);
        }
        }
        chack();
    },
    error:function(xhr, type, exception){
        Close_Div();
    }
});

}

function remove_all_float_vm(data){
show();
$.ajax({
    type:"GET",
    url: "/dashboard/admin/projects/"+ Pool_id +"/pool_remove_ajax/",
    data:{"data":data},
    dataType:"jsonp",
    jsonp:"callback",
    jsonpCallback:"match",
    success:function(data){
        var newData = data.success
        for(var i=0;i < newData.length;i++){
            $('#User_VM>ul[id='+ newData[i][1] + ']').remove();
        }
        for(var i=0;i<newData.length;i++){
            var Div_id = document.getElementById("nobind_VM");
            var ul = document.createElement("ul");
            ul.setAttribute("id", newData[i][1]);
            ul.innerHTML = "<li id=\"\" style=\"width: 85%;float: left\">"+newData[i][0]+"</li>" + 
	    "<a  href=\"javascript:add_pool_vm(\'"+newData[i][1]+"\',\'"+ newData[i][0]+"\')\" class=\"btn-primary\" style=\"text-decoration:none;\">+</a>";
            Div_id.appendChild(ul);
        }
        chack();
        Close_Div();
    },
    error:function(xhr, type, exception){
        Close_Div();
    }
});


}

$('#username ul').click(function(){
   Pool_id = $(this).attr("id");
   //chack();
   show();
   $.ajax({
       type:"GET",
       url: "/dashboard/admin/projects/"+ Pool_id +"/pool_ajax/",
       dataType:"jsonp",
       jsonp:"callback",
       jsonpCallback:"match",
       success:function(data){
           Close_Div();
           remove_ul();
           var pool_vm=data.success;
           var pool_vm_length=data.success.length;
           for(var i=0;i<pool_vm_length;i++){
               var Div_id = document.getElementById("User_VM");
               var ul = document.createElement("ul");
               ul.setAttribute("id", pool_vm[i][1]);
               ul.innerHTML = "<li style=\"width: 85%;float: left\">"+ pool_vm[i][0] +"</li>" + 
	       "<a  href=\"javascript:remove_pool_vm(\'"+pool_vm[i][1]+"\',\'"+ pool_vm[i][0]+"\')\" class=\"btn-primary\" style=\"text-decoration:none;\">-</a>";
               Div_id.appendChild(ul);
           }
       },
   });
})

function remove_pool_vm(remove_pool_id,remove_pool_name){
    // alert(pool_id + "___" + pool_name)
    show();
    $.ajax({
        type:"GET",
        url: "/dashboard/admin/projects/"+ Pool_id+ "/pool_remove_instance/?remove_instance_id="+remove_pool_id,
        dataType:"jsonp",
        jsonp:"callback",
        jsonpCallback:"match",
        success:function(msg){
        if(msg.success == "success"){
            Close_Div();
            $('#User_VM>ul[id='+ remove_pool_id +']').remove();
            var Div_id = document.getElementById("nobind_VM");
            var ul = document.createElement("ul");
            ul.setAttribute("id", remove_pool_id);
            ul.innerHTML = "<li id=\"\" style=\"width: 85%;float: left\">"+remove_pool_name+"</li>" +
                "<a  href=\"javascript:add_pool_vm(\'"+remove_pool_id+"\',\'"+ remove_pool_name+"\')\" class=\"btn-primary\" style=\"text-decoration:none;\">+</a>";
            Div_id.appendChild(ul);
        }
        chack();
        },
        error:function(xhr, type, exception){
            Close_Div();
        }
    }); 
}

function add_pool_vm(add_pool_id,add_pool_name){
    if(Pool_id != ""){
     	//alert(add_pool_id + "___" + add_pool_name + "___" + Pool_id)
     	show();
        $.ajax({
            type:"GET",
            url: "/dashboard/admin/projects/"+ Pool_id+ "/pool_add_instance/?add_instance_id="+add_pool_id,
            dataType:"jsonp",
            jsonp:"callback",
            jsonpCallback:"match",
            success:function(msg){
              if(msg.success == "success"){
                Close_Div();
                $('#nobind_VM>ul[id='+ add_pool_id + ']').remove();
                var Div_id = document.getElementById("User_VM");
                var ul = document.createElement("ul");
                ul.setAttribute("id", add_pool_id);
                ul.innerHTML = "<li id=\"\" style=\"width: 85%;float: left\">"+add_pool_name+"</li>" +
                "<a  href=\"javascript:remove_pool_vm(\'"+add_pool_id+"\',\'"+ add_pool_name+"\')\" class=\"btn-primary\" style=\"text-decoration:none;\">-</a>";
                Div_id.appendChild(ul);
              }
            chack();
            },
            error:function(xhr, type, exception){
                 Close_Div();
            }
        });
    }   
}

function chack(){
    var ss = document.getElementById("oneKeyBinding")
    //show();
    var obj_user_id = new Array()
    var userId = ""
    var Data = ""
    $.ajax({
        type:"GET",
        url: "/dashboard/admin/projects/"+ tenant_id +"/check_instances_float/",
        dataType:"jsonp",
        jsonp:"callback",
        jsonpCallback:"match",
        success:function(msg){
           if(msg.success == "success"){
                ss.innerText="Remove";
		ss.href="javascript:bind_vm()";
           }else{
                ss.innerText="Bindings";
		ss.href="javascript:bind_vm()";
           }
           //Close_Div();
        }
    })
    //if($('#User_VM ul').length <= 0){
    //    ss.innerText="Bindings";
    //    ss.href="javascript:bind_vm()"
    //}else{
    //    ss.innerText="Remove";
    //    ss.href="javascript:bind_vm();"
    //}
    //if($('#nobind_VM ul').length <= 0 ){
    //	if($('#User_VM ul').length <= 0){
    //        ss.innerText="Remove";
    //    }else{
    //        ss.innerText="Remove";
    //        ss.href="javascript:bind_vm();"
    //    }
    //}else{
    //    ss.innerText="Bindings";
    //    ss.href="javascript:bind_vm();"
    //}
    //if($('#username ul').length <= 0 || Pool_id == ''){
    //    if(ss.hasAttribute("href"))
    //        ss.removeAttribute("href");
    //}
}

chack();

function remove_ul(){
    var div = document.getElementById("User_VM");
    while(div.hasChildNodes())
    {
        div.removeChild(div.firstChild);
    }
}

function changeBackground(x)
{
    d=document.getElementsByTagName('ul')
    for(p=d.length;p--;){
        if(d[p].id!=x){d[p].style.backgroundColor='#FFFFFF'/*其他*/}
        else{d[p].style.backgroundColor='#D2D2D2'/*点击的*/}
    }
}
function show(){
    var loading_mask = document.createElement("DIV");
    loading_mask.id = "loading-mask";
    var loading = document.createElement("DIV");
    loading.id = "loading";
    var loading_indicator = document.createElement("DIV");
    loading_indicator.id="loading-indicator";
    strHtml = "<img src=\"/dashboard/static/dashboard/img/4154R.gif\" style=\"padding-left: 7px;display: block;vertical-align:top;\"/>" + "<br />";
    strHtml += "<span id=\"loading-msg\">Loading</span>";
    var Demo = document.getElementById("About");
    loading_indicator.innerHTML=strHtml;
    loading.appendChild(loading_indicator);
    Demo.appendChild(loading_mask);
    Demo.appendChild(loading);
}
function Close_Div(){
    var shield= document.getElementById("loading-mask");
    var alertFram= document.getElementById("loading");
    if(alertFram!=null) {
        document.getElementById("About").removeChild(alertFram);
    }
    if(shield!=null) {
        document.getElementById("About").removeChild(shield);
    }
}
