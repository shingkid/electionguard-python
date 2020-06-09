from typing import Iterable, List, Optional

from .key_ceremony import (
    AuxiliaryPublicKey,
    CeremonyDetails,
    ElectionJointKey,
    ElectionPartialKeyBackup,
    ElectionPartialKeyChallenge,
    ElectionPartialKeyVerification,
    ElectionPublicKey,
    GuardianDataStore,
    GuardianId,
    GuardianPair,
    PublicKeySet,
    combine_election_public_keys,
)


class KeyCeremonyMediator:
    """
    KeyCeremonyMediator for assisting communication between guardians 
    """

    ceremony_details: CeremonyDetails

    _auxiliary_public_keys: GuardianDataStore[GuardianId, AuxiliaryPublicKey]
    _election_public_keys: GuardianDataStore[GuardianId, ElectionPublicKey]
    _election_partial_key_backups: GuardianDataStore[
        GuardianPair, ElectionPartialKeyBackup
    ]
    _election_partial_key_challenges: GuardianDataStore[
        GuardianPair, ElectionPartialKeyChallenge
    ]
    _election_partial_key_verifications: GuardianDataStore[
        GuardianPair, ElectionPartialKeyVerification
    ]

    def __init__(self, ceremony_details: CeremonyDetails):
        self.ceremony_details = ceremony_details
        self._auxiliary_public_keys = GuardianDataStore[
            GuardianId, AuxiliaryPublicKey
        ]()
        self._election_public_keys = GuardianDataStore[GuardianId, ElectionPublicKey]()
        self._election_partial_key_backups = GuardianDataStore[
            GuardianPair, ElectionPartialKeyBackup
        ]()
        self._election_partial_key_verifications = GuardianDataStore[
            GuardianPair, ElectionPartialKeyVerification
        ]()
        self._election_partial_key_challenges = GuardianDataStore[
            GuardianPair, ElectionPartialKeyChallenge
        ]()

    def reset(self, ceremony_details: CeremonyDetails) -> None:
        """
        Reset mediator to initial state
        :param ceremony_details: Ceremony details of election
        """
        self.ceremony_details = ceremony_details
        self._auxiliary_public_keys.clear()
        self._election_public_keys.clear()
        self._election_partial_key_backups.clear()
        self._election_partial_key_challenges.clear()
        self._election_partial_key_verifications.clear()

    # Attendance
    def confirm_presence_of_guardian(self, public_key_set: PublicKeySet) -> None:
        """
        Confirm presence of guardian by passing their public key set
        :param public_key_set: Public key set
        """
        self.receive_auxiliary_public_key(
            AuxiliaryPublicKey(
                public_key_set.owner_id,
                public_key_set.sequence_order,
                public_key_set.auxiliary_public_key,
            )
        )
        self.receive_election_public_key(
            ElectionPublicKey(
                public_key_set.owner_id,
                public_key_set.election_public_key_proof,
                public_key_set.election_public_key,
            ),
        )

    def all_guardians_in_attendance(self) -> bool:
        """
        Check the attendance of all the guardians expected
        :return: True if all guardians in attendance
        """
        return (
            self.all_auxiliary_public_keys_available()
            and self.all_election_public_keys_available()
        )

    def share_guardians_in_attendance(self) -> Iterable[GuardianId]:
        """
        Share a list of all the guardians in attendance
        :return: list of guardians ids
        """
        return self._election_public_keys.keys()

    # Auxiliary Public Keys
    def receive_auxiliary_public_key(self, public_key: AuxiliaryPublicKey) -> None:
        """
        Receive auxiliary public key from guardian
        :param public_key: Auxiliary public key
        """
        self._auxiliary_public_keys.set(public_key.owner_id, public_key)

    def all_auxiliary_public_keys_available(self) -> bool:
        """
        True if all auxiliary public key for all guardians available
        :return: All auxiliary public backups for all guardians available
        """
        return (
            self._auxiliary_public_keys.length()
            == self.ceremony_details.number_of_guardians
        )

    def share_auxiliary_public_keys(self) -> Iterable[AuxiliaryPublicKey]:
        """
        Share all currently stored auxiliary public keys for all guardians
        :return: list of auxiliary public keys
        """
        return self._auxiliary_public_keys.values()

    # Election Public Keys
    def receive_election_public_key(self, public_key: ElectionPublicKey) -> None:
        """
        Receive election public key from guardian
        :param public_key: election public key
        """
        self._election_public_keys.set(public_key.owner_id, public_key)

    def all_election_public_keys_available(self) -> bool:
        """
        True if all election public keys for all guardians available
        :return: All election public keys for all guardians available
        """
        return (
            self._election_public_keys.length()
            == self.ceremony_details.number_of_guardians
        )

    def share_election_public_keys(self) -> Iterable[ElectionPublicKey]:
        """
        Share all currently stored election public keys for all guardians
        :return: list of election public keys
        """
        return self._election_public_keys.values()

    # Election Partial Key Backups
    def receive_election_partial_key_backup(
        self, backup: ElectionPartialKeyBackup
    ) -> None:
        """
        Receive election partial key backup from guardian
        :param backup: Election partial key backup
        """
        if backup.owner_id == backup.designated_id:
            return
        self._election_partial_key_backups.set(
            GuardianPair(backup.owner_id, backup.designated_id), backup
        )

    def all_election_partial_key_backups_available(self) -> bool:
        """
        True if all election partial key backups for all guardians available
        :return: All election partial key backups for all guardians available
        """
        required_backups_per_guardian = self.ceremony_details.number_of_guardians - 1
        return (
            self._election_partial_key_backups.length()
            == required_backups_per_guardian * self.ceremony_details.number_of_guardians
        )

    def share_election_partial_key_backups_to_guardian(
        self, guardian_id: GuardianId
    ) -> List[ElectionPartialKeyBackup]:
        """
        Share all election partial key backups for designated guardian
        :param guardian_id: Recipients guardian id
        :return: List of guardians designated backups
        """
        backups: List[ElectionPartialKeyBackup] = []
        for current_guardian_id in self.share_guardians_in_attendance():
            if guardian_id != current_guardian_id:
                backup = self._election_partial_key_backups.get(
                    GuardianPair(current_guardian_id, guardian_id)
                )
                if backup is not None:
                    backups.append(backup)
        return backups

    # Partial Key Verifications
    def receive_election_partial_key_verification(
        self, verification: ElectionPartialKeyVerification
    ) -> None:
        """
        Receive election partial key verification from guardian
        :param verification: Election partial key verification
        """
        if verification.owner_id == verification.designated_id:
            return
        self._election_partial_key_verifications.set(
            GuardianPair(verification.owner_id, verification.designated_id),
            verification,
        )

    def all_election_partial_key_verifications_received(self) -> bool:
        """
        True if all election partial key verifications recieved
        :return: All election partial key verifications received
        """
        required_verifications_per_guardian = (
            self.ceremony_details.number_of_guardians - 1
        )
        return (
            self._election_partial_key_verifications.length()
            == required_verifications_per_guardian
            * self.ceremony_details.number_of_guardians
        )

    def all_election_partial_key_backups_verified(self) -> bool:
        """
        True if all election partial key backups verified
        :return: All election partial key backups verified
        """
        if not self.all_election_partial_key_verifications_received():
            return False
        for verification in self._election_partial_key_verifications.values():
            if not verification.verified:
                return False
        return True

    # Partial Key Challenges
    def share_failed_partial_key_verifications(self) -> List[GuardianPair]:
        """
        Share list of guardians with failed partial key backup verifications
        :return: List of guardian pairs with failed verifications
        """
        failed_verifications: List[GuardianPair] = []
        for pair, verification in self._election_partial_key_verifications.items():
            if not verification.verified:
                failed_verifications.append(pair)
        return failed_verifications

    def share_missing_election_partial_key_challenges(self) -> List[GuardianPair]:
        """
        Share list of guardians with missing election partial key challenges
        :return: List of guardian pairs with failed verifications and no challenges
        """
        failed_verifications = self.share_failed_partial_key_verifications()
        for pair in self._election_partial_key_challenges.keys():
            failed_verifications.remove(pair)
        return failed_verifications

    def receive_election_partial_key_challenge(
        self, challenge: ElectionPartialKeyChallenge
    ) -> None:
        """
        Receive an election partial key challenge from a guardian with a failed verification
        :param challenge: Election partial key challenge
        """
        self._election_partial_key_challenges.set(
            GuardianPair(challenge.owner_id, challenge.designated_id), challenge
        )

    def share_open_election_partial_key_challenges(
        self,
    ) -> List[ElectionPartialKeyChallenge]:
        """
        Share all open election partial key challenges with guardians
        :return: List of open election partial key challenges 
        """
        return list(self._election_partial_key_challenges.values())

    # Publish Joint Key
    def publish_joint_key(self) -> Optional[ElectionJointKey]:
        """
        Publish joint election key from the public keys of all guardians
        :return: Optional joint key for election
        """
        if not self.all_election_public_keys_available():
            return None
        if not self.all_election_partial_key_backups_verified():
            return None
        return combine_election_public_keys(self._election_public_keys)