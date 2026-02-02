import { useUIStore } from '@/stores'

export const useModal = () => {
  const { currentModal, actions } = useUIStore()

  const openModal = (modal: string) => {
    actions.openModal(modal)
  }

  const closeModal = () => {
    actions.closeModal()
  }

  return {
    currentModal,
    isOpen: currentModal !== null,
    openModal,
    closeModal,
  }
}
