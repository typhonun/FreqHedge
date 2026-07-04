<template>

<el-container class="layout">

    <el-aside width="240px">

        <div class="logo">
            DcaTp Manager
        </div>

        <el-menu
            router
            :default-active="$route.path"
            class="side-menu"
        >

            <el-menu-item index="/">
                仪表盘
            </el-menu-item>

            <el-menu-item index="/control">
                控制中心
            </el-menu-item>

            <el-menu-item index="/positions">
                策略配置
            </el-menu-item>

            <el-menu-item index="/history">
                交易历史
            </el-menu-item>

            <el-menu-item index="/charts">
                K线分析
            </el-menu-item>

            <el-menu-item index="/logs">
                系统日志
            </el-menu-item>

        </el-menu>

    </el-aside>

    <el-main>
        <router-view />
    </el-main>

</el-container>

</template>

<style scoped>

.layout{
    height:100vh;
}

.el-aside{
    background:#001529;
    display:flex;
    flex-direction:column;
}

.logo{

    height:70px;

    display:flex;
    align-items:center;
    justify-content:center;

    color:white;

    font-size:22px;
    font-weight:700;

    border-bottom:1px solid rgba(255,255,255,.1);
}

.side-menu{
    height:100%;
    display:flex;
    flex-direction:column;
}

.side-menu .el-menu-item{

    flex:1;

    display:flex;
    align-items:center;
    justify-content:center;

    font-size:18px;
}

.el-main{

    background:#f5f7fa;

    padding:20px;

    overflow:auto;
}

</style>