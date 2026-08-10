<template>

<el-card class="status-wrapper">

    <el-row :gutter="20">


        <!-- 多头 -->

        <el-col :span="12">

            <el-card class="bot-card">

                <div class="title">
                    📈 多头机器人
                </div>


                <div class="status">


                    <span
                        class="light"
                        :class="
                            longState === 'RUNNING'
                            ? 'running'
                            : 'stopped'
                        "
                    />


                    <span
                        :class="
                            longState === 'RUNNING'
                            ? 'running-text'
                            : 'stopped-text'
                        "
                    >

                        {{ longState }}

                    </span>


                </div>


            </el-card>


        </el-col>




        <!-- 空头 -->

        <el-col :span="12">


            <el-card class="bot-card">


                <div class="title">
                    📉 空头机器人
                </div>


                <div class="status">


                    <span
                        class="light"
                        :class="
                            shortState === 'RUNNING'
                            ? 'running'
                            : 'stopped'
                        "
                    />


                    <span
                        :class="
                            shortState === 'RUNNING'
                            ? 'running-text'
                            : 'stopped-text'
                        "
                    >

                        {{ shortState }}

                    </span>


                </div>


            </el-card>


        </el-col>



    </el-row>


</el-card>


</template>



<script setup>


import {
    onMounted,
    onUnmounted
} from "vue"


import {
    useStatus
} from "../composables/useStatus"



const {

    longState,

    shortState,

    loadStatus

}=useStatus()



let timer=null



onMounted(()=>{


    loadStatus()


    timer=setInterval(()=>{


        loadStatus()


    },3000)


})



onUnmounted(()=>{


    if(timer){

        clearInterval(timer)

    }


})



</script>



<style scoped>


.status-wrapper{

    border-radius:14px;

}



.bot-card{

    border-radius:14px;

    transition:.3s;

}



.bot-card:hover{

    transform:translateY(-3px);

    box-shadow:
    0 8px 25px rgba(0,0,0,.12);

}



.title{

    font-size:18px;

    font-weight:600;

    margin-bottom:18px;

}



.status{

    display:flex;

    align-items:center;

    gap:10px;

}



.light{

    width:10px;

    height:10px;

    border-radius:50%;

}



.running{

    background:#67c23a;

    box-shadow:
    0 0 6px #67c23a,
    0 0 12px #67c23a;

}



.stopped{

    background:#f56c6c;

    box-shadow:
    0 0 6px #f56c6c;

}



.running-text{

    color:#67c23a;

    font-weight:600;

}



.stopped-text{

    color:#f56c6c;

    font-weight:600;

}


</style>