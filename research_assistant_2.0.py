import os
import httpx
import PyPDF2
import docx
from openai import OpenAI
import streamlit as st


class ResearchAssistant:
    def __init__(self):
        # 1. Clear proxy variables from environment to prevent interception
        for key in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"]:
            os.environ.pop(key, None)
        os.environ["NO_PROXY"] = "*"

        # 2. Force httpx to ignore system/environment proxy settings
        http_client = httpx.Client(trust_env=False)

        # 3. Connect using 127.0.0.1
        self.client = OpenAI(
            api_key='ollama',
            base_url='http://127.0.0.1:11434/v1',
            http_client=http_client
        )
        self.model = 'deepseek-r1:1.5b'

    def extract_text(self, uploaded_file):
        text = ''
        try:
            if uploaded_file.type == 'application/pdf':
                pdf_reader = PyPDF2.PdfReader(uploaded_file)
                for page in pdf_reader.pages:
                    extracted = page.extract_text()
                    if extracted:
                        text += extracted
            elif uploaded_file.type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
                doc = docx.Document(uploaded_file)
                for para in doc.paragraphs:
                    text += para.text + '\n'
            else:
                text = str(uploaded_file.read(), 'utf-8')
        except Exception as e:
            st.error(f"Error reading {uploaded_file.name}: {e}")
        return text

    def analyze_content(self, text, query, container):
        if not text.strip():
            container.warning("No readable text found in document.")
            return

        prompt = f"""Analyze this text and answer the query:
        Text: {text[:3000]}...
        Query: {query}

        Provide:
        1. Direct answer to the query
        2. Supporting evidence
        3. Key findings
        4. Limitations of the Analysis
        """

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {'role': 'system', 'content': 'You are a research assistant.'},
                    {'role': 'user', 'content': prompt},
                ],
                stream=True
            )
            
            with container:
                result = st.empty()
                collected_chunks = []
                for chunk in response:
                    if chunk.choices and chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        collected_chunks.append(content)
                        result.markdown(''.join(collected_chunks))
                        
        except Exception as e:
            container.error(f'API Communication Error: {str(e)}')


def main():
    st.set_page_config(page_title='Research Assistant', layout='wide')
    st.title('Research Document Analyzer')
    assistant = ResearchAssistant()

    with st.sidebar:
        st.header('Upload Documents')
        uploaded_files = st.file_uploader(
            'Upload research documents',
            type=['pdf', 'docx', 'txt'],
            accept_multiple_files=True,
        )

    if uploaded_files:
        st.write(f"**{len(uploaded_files)} documents uploaded**")

        query = st.text_area(
            'What would you like to know about these documents?',
            placeholder='Example: What are the main findings?',
            height=100,
        )

        if st.button('Analyze', type='primary'):
            if not query.strip():
                st.warning("Please enter a query first.")
                return

            for file in uploaded_files:
                st.markdown(f"## 📄 Document: `{file.name}`")
                text = assistant.extract_text(file)

                with st.expander("📌 Main Analysis", expanded=True):
                    assistant.analyze_content(text, query, st.container())

                with st.expander("🔑 Key Points", expanded=False):
                    assistant.analyze_content(text, "Extract key points from this text.", st.container())

                with st.expander("📝 Brief Summary", expanded=False):
                    assistant.analyze_content(text, "Provide a brief summary of this text.", st.container())


if __name__ == '__main__':
    main()