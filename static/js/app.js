$(document).ready(function(){
    $("#but_text").click(function(){
        var search = $('#search').val();
        $.ajax({
            url: '/text_gen',
            type: 'post',
            data: {search:search},
            beforeSend: function(){
                $("#loader").show();
            },
            success: function(response){
                $('.response').empty();
                $('.response').append(response.htmlresponse);
            },
            complete:function(data){
                $("#loader").hide();
            }
        });
    });
    $("#but_video").click(function(){
        $.ajax({
            url: '/video_gen',
            type: 'post',
            beforeSend: function(){
                $("#loader").show();
            },
            success: function(response){
                $('.response').empty();
                $('.response').append(response.htmlresponse);
                
            },
            complete:function(data){
                $("#loader").hide();
               
            }
        });
    });
});