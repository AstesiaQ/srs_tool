import streamlit as st
import pandas as pd
from crewai import Agent, Task, Crew, LLM

import docx
import io
import csv

if "password" not in st.session_state:
    password = st.text_input("请输入密码", type="password")
    if st.button("提交"):
        if password == "3321":
            st.session_state.password = True
            st.rerun()
        else:
            st.error("密码错误")

else:
    # 设置页面标题
    st.title("软件需求点分析工具")

    # 上传文件功能
    uploaded_file = st.file_uploader("请上传包含软件需求的docx文件", type="docx")

    # 定义函数来读取docx文件内容
    def read_docx(file):
        doc = docx.Document(file)
        full_text = []
        for para in doc.paragraphs:
            full_text.append(para.text)
        return '\n'.join(full_text)

    # 当用户上传文件后执行分析
    if uploaded_file is not None:
        # 读取文件内容
        file_content = read_docx(uploaded_file)
        
        # 显示处理状态
        with st.spinner('正在分析软件需求点...'):
            # 创建OpenAI模型
            
            ds_r1 = LLM(
            model="deepseek/deepseek-reasoner",
            api_key=st.secrets.deepseek_api_key
            )
            
            # 创建需求提取Agent
            requirement_extractor = Agent(
                role="需求提取专家",
                goal="从文档中提取软件需求点",
                backstory="你是一位经验丰富的软件需求分析师，擅长从文档中识别和提取关键的软件需求点。",
                llm=ds_r1,
                verbose=True
            )
            
            # 创建需求分类Agent
            requirement_classifier = Agent(
                role="需求分类专家",
                goal="将软件需求点按照以下类别进行分类：ILF，EIF，EO，EI，EQ，NA",
                backstory="你是一位专业的软件需求分类专家，能够准确判断需求点的类别。",
                llm=ds_r1,
                verbose=True
            )
            
            # 创建提取需求点的任务
            extraction_task = Task(
                description=f"分析以下文档内容，提取所有软件需求点。每个需求点应包含需求名称和需求概述。\n\n{file_content}",
                agent=requirement_extractor,
                expected_output="以JSON格式返回需求点列表，每个需求点包含'name'和'description'字段"
            )
            
            # 创建分类任务
            classification_task = Task(
                description="""将提供的软件需求点分类为ILF（内部逻辑文件）、EIF（外部接口文件）、EI（外部输入）、EO（外部输出）、EQ（外部查询），五种功能点类型,
                以下是分类规则：规则1：ILF识别规则：ILF是系统内部维护的逻辑上的一组业务数据。识别ILF的基本步骤如下：
                a) 识别业务对象。业务对象应是用户可理解和识别的，包括业务数据或业务规则。
                注：为程序处理而维护的数据属于编码数据。所有的编码数据均不应识别为逻辑文件，与之相关的操作也不应识别
                为基本过程；
                b) 确定逻辑文件数量。根据业务上的逻辑差异及从属关系确定逻辑文件的数量。
                c) 是否是 ILF。确定该逻辑文件是否在本系统内进行维护。如果是，记为 ILF；否则为 EIF。
                d）最终的功能点分类中，每个ILF只能出现一次。

                规则2：EIF识别规则：EIF是被应用边界内一个或几个基本处理过程所引用的业务数据。一个应用中的EIF应是其他应用
                中的ILF。识别EIF的基本步骤如下：
                a) 识别业务对象。业务对象应该应是用户可理解和识别的。业务对象包括业务数据或业务规则。
                而一些为了程序处理而维护的数据则属于编码数据。所有的编码数据均不识别为逻辑文件，与
                之相关的操作也不识别为基本过程；
                b) 确定逻辑文件数量。需要根据业务上的逻辑差异及从属关系确定逻辑文件的数量。
                c) 是否是 EIF。确定该逻辑文件是否在本系统内进行维护。如果是，记为 ILF；否则为 EIF。
                d）最终的功能点分类中，每个EIF只能出现一次。

                规则3：EI识别规则：EI是处理来自系统边界之外的数据或控制信息的过程。目的是维护一个或多个ILF或者改变系统的
                行为。识别EI的基本规则如下：
                a) 应是来自系统边界之外的输入数据或控制信息；
                b) 穿过边界的数据应是改变系统行为的控制信息或者应至少维护一个 ILF；
                c) 该 EI 不应被重复计数。任何被分别计数的两个 EI 至少满足下面三个条件之一（否则应视为
                同一 EI）：
                1) 涉及的 ILF 或 EIF 不同；
                2) 涉及的数据元素不同；
                3) 处理逻辑不同。


                规则4：EQ识别规则：EQ是向系统边界之外发送数据或控制信息的基本处理过程。目的是向用户呈现未经加工的己有信
                息。识别EQ的基本规则如下：
                a) 将数据或控制信息发送岀系统边界。
                b) 处理逻辑可包含筛选、分组或排序。
                c) 处理逻辑不应包含：
                1) 数学公式或计算过程；
                2) 产生衍生数据；
                3) 维护 ILF；
                4) 改变系统行为。
                d) 该 EQ 不应被重复计数。任何被分别计数的两个 EQ 至少满足下面一个条件标准则被视为同一
                EQ）:
                1) 涉及的 ILF 或 EIF 不同；
                2) 涉及的数据元素不同；
                3) 处理逻辑不同。


                规则5：EO识别规则：EO是处理向系统边界之外发送数据或控制信息的过程。目的是向用户呈现经过处理的信息。识别EO
                的基本规则如下：
                a) 将数据或控制信息发送岀系统边界；
                b) 处理逻辑应至少符合以下一种情况：
                1) 包含至少一个数学公式或计算过程；
                2) 产生衍生数据；
                3) 维护至少一个 ILF；
                4) 改变系统行为。
                c) 该 EO 不应被重复计数。任何被分别计数的两个 EO 至少满足下面一个条件（否则被视为同一
                EO）:
                1) 涉及的 ILF 或 EIF 不同；
                2) 涉及的数据元素不同；
                3) 处理逻辑不同。
                若你认为该功能点不属于任何一类，则标记为NA""",
                agent=requirement_classifier,
                expected_output="为每个需求点添加'type'字段，该字段值应为ILF，EIF，EO，EI，EQ，NA中的一个。",
                context=[extraction_task]
            )
            
            # 创建Crew并运行任务
            crew = Crew(
                agents=[requirement_extractor, requirement_classifier],
                tasks=[extraction_task, classification_task],
                verbose=True
            )
            
            # 执行分析
            results = crew.kickoff().raw

            st.write(results)

            # for result in results:
            #     st.write(f"功能名称:{result["name"]}\n功能描述:{result["description"]}\n功能分类:{result["type"]}")
            
        
            
            
    else:
        st.info("请上传一个docx文件以开始分析")
