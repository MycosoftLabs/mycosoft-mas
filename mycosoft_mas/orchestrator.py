    async def _initialize_document_knowledge_base(self):
        """Initialize document knowledge base for agent access."""
        try:
            from mycosoft_mas.services.document_knowledge_base import DocumentKnowledgeBase
            
            self.document_knowledge_base = DocumentKnowledgeBase()
            await self.document_knowledge_base.initialize()
            
            self.logger.info("Document knowledge base initialized")
        except Exception as e:
            self.logger.warning(f"Could not initialize document knowledge base: {str(e)}")
            self.document_knowledge_base = None
