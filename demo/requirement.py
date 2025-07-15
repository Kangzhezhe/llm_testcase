from rag import build_multi_file_knowledge_base, show_chroma_collection


def main():
    # 定义需要处理的文件列表
    file_list = [
        {"file_path": "D:\\testcase\\aitestcases\\data\\需求文件\\需求分析报告-湖北中烟新型烟草产品调研与开发信息反馈系统项目.docx",
         "type": "需求文档"},
        {"file_path": "D:\\testcase\\aitestcases\\data\\需求文件\\湖北中烟工程中心数字管理应用用户操作手册v1.0.docx",
         "type": "用户手册"},
        {"file_path": "D:\\testcase\\aitestcases\\data\\需求文件\\数字信息化管理应用系统接口文档.docx",
         "type": "技术文档"}
    ]

    # 构建知识库
    collection = build_multi_file_knowledge_base(file_list,max_len=1000)

    # 显示知识库内容
    print("知识库内容：")
    docs = show_chroma_collection(meta_filter={"type": "需求文档"})
    for doc in docs:
        print(doc)

if __name__ == "__main__":
    main()