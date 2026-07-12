<template>

<el-card>

<h2>
历史收益
</h2>


<el-row :gutter="20">


<el-col :span="8">

<el-statistic
title="多单历史收益"
:value="Number(profit.long_closed_profit || 0)"
:precision="2"
/>

</el-col>



<el-col :span="8">

<el-statistic
title="空单历史收益"
:value="Number(profit.short_closed_profit || 0)"
:precision="2"
/>

</el-col>



<el-col :span="8">

<el-statistic
title="总历史收益"
:value="Number(profit.total_closed_profit || 0)"
:precision="2"
/>

</el-col>


</el-row>


</el-card>


</template>


<script setup>

defineProps({

profit:{
type:Object,
default:()=>({})
}

})

</script>