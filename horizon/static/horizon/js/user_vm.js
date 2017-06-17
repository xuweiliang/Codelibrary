 var global_userId = "";
 var tenant_ID=document.getElementById("tenant_id").value;
 var radioNum="";
 //请求用户绑定的虚拟机列表
$('#username ul').click(function(){
   var User_id = $(this).attr("id");
   global_userId = User_id;
   $.ajax({
       type:"GET",
//       url: "/dashboard/admin/projects/"+User_id +"/instance_ajax/?tenant_id="+tenant_ID,
       url: "/dashboard/admin/projects/"+tenant_ID +"/instance_ajax/?user_id="+User_id,
       dataType:"jsonp",
       jsonp:"callback",
       jsonpCallback:"match",
       success:function(data){ 
   	remove_ul();     //删除ul 
   	 var user_vm=data.success;
           var user_vm_length=data.success.length;
           //把用户绑定的虚拟机列表显示到div
           for(var i=0;i<user_vm_length;i++){
               var Div_id = document.getElementById("User_VM");
               var ul = document.createElement("ul");
   	    ul.setAttribute("id", user_vm[i][1]);
               ul.innerHTML = "<li style=\"width: 85%;float: left\">"+ user_vm[i][0] +"</li>" +
                              "<a  href=\"javascript:remove_user_vm(\'"+user_vm[i][1]+"\',\'"+ user_vm[i][0]+"\')\" class=\"btn-primary\" style=\"text-decoration:none;\">-</a>";
               Div_id.appendChild(ul);
           }
       },
   });
})
function remove_ul(){
    var div = document.getElementById("User_VM");
    while(div.hasChildNodes()) 
    {
        div.removeChild(div.firstChild);
    }
}
function remove_user_vm(remove_user_vm_id,remove_user_vm_name){
    show();
    $.ajax({
        type:"GET",
        //url: "/dashboard/admin/projects/"+ remove_user_vm_id+ "/user_remove/?tenant_id="+tenant_ID,
        url: "/dashboard/admin/projects/"+ tenant_ID+ "/user_remove/?instance_id="+remove_user_vm_id,
        dataType:"jsonp",
        jsonp:"callback",
        jsonpCallback:"match",
        success:function(msg){
	if(msg.success == "success"){
	    Close_Div();
    	    $('#User_VM>ul[id='+ remove_user_vm_id +']').remove();
    	    var Div_id = document.getElementById("nobind_VM");
    	    var ul = document.createElement("ul");
    	    ul.setAttribute("id", remove_user_vm_id);
    	    ul.innerHTML =  "<input type='radio' name='radio' value="+remove_user_vm_id+" style='float:left;margin-top: 13px;margin-left: 0px;' onclick='show_selected_item_val(this)'>"+
			    "<li id=\"\" style=\"width: 77%;float: left\">"+remove_user_vm_name+"</li>" +
        		    "<a  href=\"javascript:addVmToUser(\'"+remove_user_vm_id+"\',\'"+ remove_user_vm_name+"\')\" class=\"btn-primary\" style=\"text-decoration:none;\">+</a>";
    	    Div_id.appendChild(ul);
	}
    	check();
        },
        error:function(xhr, type, exception){
	    Close_Div();
        }
    });
}
function addVmToUser( vm_id,vm_name){
    if(global_userId != ""){
	show();
        $.ajax({
            type:"GET",
            //url: "/dashboad/admin/projects"+ vm_id+ "/add_instance/?tenant_id="+tenant_ID+"&user_id="+ global_userId,
            url: "/dashboard/admin/projects/"+tenant_ID+ "/add_instance/?vm_id="+vm_id+"&user_id="+ global_userId,
            dataType:"jsonp",
            jsonp:"callback",
            jsonpCallback:"match",
            success:function(msg){
	      if(msg.success == "success"){
		Close_Div();
    	        $('#nobind_VM>ul[id='+ vm_id +']').remove();
        	var Div_id = document.getElementById("User_VM");
        	var ul = document.createElement("ul");
        	ul.setAttribute("id", vm_id);
        	ul.innerHTML = "<li id=\"\" style=\"width: 85%;float: left\">"+vm_name+"</li>" +
            	"<a  href=\"javascript:remove_user_vm(\'"+vm_id+"\',\'"+ vm_name+"\')\" class=\"btn-primary\" style=\"text-decoration:none;\">-</a>";
        	Div_id.appendChild(ul);
	      }
	    check();
            },
            error:function(xhr, type, exception){
	    	 Close_Div();
            }
        });
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
//function checkUserInstances(data){
//   var ss=""
//   $.ajax({
//	type:"GET",
//	url: "../../"+ tenant_ID +"/check_instances/",
//    	data:{"data":data},
//        dataType:"jsonp",
//        jsonp:"callback",
//        jsonpCallback:"match",
//        success:function(msg){
//	   if(msg.success == "success"){
//		alert(msg.success)
//           	ss = "yes"
//	   }else{
//		ss = "no"
//	   }
//	}
//    }) 
//    return ss
//}

function check(){
    show();
    var obj_user_id = new Array() 
    var userId = ""
    var Data = ""
    var success=""
    $("#username ul").each(function(i,dom){
        userId += dom.id + ","
    });
    obj_user_id = userId.substring(0,userId.length - 1).split(',')
    obj_user_length = obj_user_id.length
    for(var i=0;i<obj_user_length;i++){
        Data += "\"" + obj_user_id[i] + "\"" + ","
    }
    Data = "[" + Data.substring(0,Data.length - 1) + "]"
    $.ajax({
        type:"GET",
        //url: "../../"+ tenant_ID +"/check_instances/",
        url: "/dashboard/admin/projects/"+ tenant_ID +"/check_instances/",
        data:{"data":Data},
        dataType:"jsonp",
        jsonp:"callback",
        jsonpCallback:"match",
        success:function(msg){
           if(msg.success == "success"){
		document.getElementById("oneKeyBinding").innerHTML="Remove";
           }else{
		document.getElementById("oneKeyBinding").innerHTML="Bindings";
           }
	   Close_Div();
    var ss = document.getElementById("oneKeyBinding")
    if($('#username ul').length <= 0){
        if(ss.hasAttribute("href")){
            ss.removeAttribute("href");
	} 
    }
    if(ss.innerHTML == "Bindings" & radioNum == ""){
        if(ss.hasAttribute("href")){
            ss.removeAttribute("href");
        }
    }else {
	ss.setAttribute("href","javascript:bind_vm()")
    }
    }
    })
}
var i = 0
$("input[name='radio']").each(function(i){
    if(i == 0){
	$(this).attr("checked","true")
    	radioNum=$(this).val();
	i++
    }
});

check();
function show_selected_item_val($item){
    radioNum=$item.value
    check()
}
function bind_vm(){
    var userName_list=""
    var noBindVm_list=""
    var obj_user = new Array()
    var obj_nobind = new Array()
    var Data=""
    var k;
    var text = document.getElementById("oneKeyBinding").innerText
    $("#username ul").each(function(i,dom){
        userName_list += dom.id + ","
    });
    obj_user = userName_list.substring(0,userName_list.length - 1).split(',')
    if(text == "Remove"){
	if(obj_user[0] == ''){
        }else{
            for(var i=0;i<obj_user_length;i++){
                Data += "\"" + obj_user[i] + "\"" + ","
            }
            Data = "[" + Data.substring(0,Data.length - 1) + "]"
            send_removeData(Data)
        }
    }
    if(text == "Bindings"){
	$("#nobind_VM ul").each(function(i,dom){
            noBindVm_list += dom.id + ","
        });
	obj_nobind = noBindVm_list.substring(0,noBindVm_list.length - 1).split(',')
        for(var i=0;i<obj_nobind.length;i++){
	    if(obj_nobind[i] == radioNum){
		k = i
		break;
	    }
	}
        for(var i=0;i<obj_user.length;i++){
            if(obj_user[i] != undefined ){
                if(i <= obj_nobind.length -1){
                    if(obj_nobind[i+k] != undefined){
                        Data += "[\"" + obj_user[i] +"\",\"" + obj_nobind[i+k] + "\"],"
                    }
		}
            }
        }
        Data = "[" + Data.substring(0,Data.length - 1) + "]"
        send_bindData(Data)
    }
}

function send_bindData(data_str){
show();
$.ajax({
    type:"GET",
    url: "/dashboard/admin/projects/"+ tenant_ID +"/batch_binding/",
    data:{"data":data_str},
    dataType:"jsonp",
    jsonp:"callback",
    jsonpCallback:"match",
    success:function(data){
        if(data.success){
            var newData=data.success
            Close_Div();
            if( global_userId == ""){
                remove_ul();
                for(var i=0;i < newData.length;i++){
                   $('#nobind_VM>ul[id='+ newData[i][1] + ']').remove();
                }
                var Div_id = document.getElementById("User_VM");
                var ul = document.createElement("ul");
                ul.setAttribute("id",newData[0][1] );
                ul.innerHTML = "<li id=\"\" style=\"width: 85%;float: left\">"+newData[0][0]+"</li>" +
                "<a  href=\"javascript:remove_user_vm(\'"+newData[0][1]+"\',\'"+ newData[0][0]+"\')\" class=\"btn-primary\" style=\"text-decoration:none;\">-</a>";
                Div_id.appendChild(ul);
            }else{
                for(var i=0;i < newData.length;i++){
                   $('#nobind_VM>ul[id='+ newData[i][1] + ']').remove();
                }
                for(var i=0;i<newData.length;i++){
                    if(global_userId == newData[i][2]){
                        var Div_id = document.getElementById("User_VM");
                        var ul = document.createElement("ul");
                        ul.setAttribute("id",newData[i][1] );
                        ul.innerHTML = "<li id=\"\" style=\"width: 85%;float: left\">"+newData[i][0]+"</li>" +
                        "<a  href=\"javascript:remove_user_vm(\'"+newData[i][1]+"\',\'"+ newData[i][0]+"\')\" class=\"btn-primary\" style=\"text-decoration:none;\">-</a>";
                        Div_id.appendChild(ul);
                    }
                }
            }
      }
    check();
    },
    error:function(xhr, type, exception){
        Close_Div();
    }
});

}


function send_removeData(data_str){
   show();
   $.ajax({
    	type:"GET",
    	//url: "../../"+ tenant_ID +"/remove_all_instance/",
    	url: "/dashboard/admin/projects/"+ tenant_ID +"/remove_all/",
    	data:{"data":data_str},
    	dataType:"jsonp",
    	jsonp:"callback",
    	jsonpCallback:"match",
    	success:function(data){
   	    if(data.success){
   	    	var newData=data.success
		remove_ul();
   	        Close_Div();
                for(var i=0;i<newData.length;i++){
   		    //var Div_id = document.getElementById("form_nobind");
    	            var Div_id = document.getElementById("nobind_VM");
   		    var ul = document.createElement("ul");
   		    ul.setAttribute("id", newData[i][1]);
   		    ul.innerHTML = "<input type='radio' name='radio' value="+newData[i][1]+" style='float:left;margin-top: 13px;margin-left: 0px;' onclick='show_selected_item_val(this)'>"+
				   "<li id=\"\" style=\"width: 77%;float: left\">"+newData[i][0]+"</li>" +
   		                   "<a  href=\"javascript:addVmToUser(\'"+newData[i][1]+"\',\'"+ newData[i][0]+"\')\" class=\"btn-primary\" style=\"text-decoration:none;\">+</a>";
   		    Div_id.appendChild(ul);	    
                }
    	    }
	    document.getElementById("oneKeyBinding").removeAttribute("href");
	    document.getElementById("oneKeyBinding").innerHTML="Bindings";
    	},
     	error:function(xhr, type, exception){
             Close_Div();
     	}
   }); 
}

function show(){
    var loading_mask = document.createElement("DIV");
    loading_mask.id = "loading-mask";
    var loading = document.createElement("DIV");
    loading.id = "loading";
    var loading_indicator = document.createElement("DIV");
    loading_indicator.id="loading-indicator";
    strHtml = "<img src=\"/dashboard/static/dashboard/img/4154R.gif\" style=\"padding-left: 7px;display: block;vertical-align:top;\"/>" + "<br />";
    //strHtml = "<img src=\"../../../../../../static/dashboard/img/4154R.gif\" style=\"padding-left: 7px;display: block;vertical-align:top;\"/>" + "<br />";
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

